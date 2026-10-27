"""Split Settings: duration, mode, output location, estimate and the Start button."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox,
                               QRadioButton, QVBoxLayout, QWidget)

from core.models import SplitJob
from core.naming import (find_existing_parts, output_extension, part_filename, sanitize_name, unique_output_dir)
from core.planner import MIN_SEGMENT_SECONDS, estimate_part_count, plan_split, validate_segment
from ui.dialogs import FFmpegSetupDialog, ask_overwrite, confirm, copy_text, pick_folder, pick_video, show_error
from ui.state import PAGE_PROGRESS, PAGE_VIDEO, AppState
from ui.widgets import (Card, DurationField, IconButton, IconLabel, ResponsiveRow, ScrollPage, elide, make_label,
                        set_role)
from utils.disk import free_space
from utils.paths import open_folder
from utils.timefmt import format_hms, format_human, hms_to_seconds, human_size, split_hms

log = logging.getLogger("msp.split_page")

PRESETS = [("5 min", 300), ("10 min", 600), ("15 min", 900), ("30 min", 1800), ("1 hour", 3600)]


class SplitPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self._syncing = False
        self.add_header("Split Settings", "Decide how long each part should be, then press Start.")

        # --- no video yet --------------------------------------------------
        self.empty = Card(orientation="h", spacing=14)
        self.empty.layout_.addWidget(IconLabel("video", 28, "muted"))
        self.empty.layout_.addWidget(make_label("No video selected yet. Pick a movie to see an estimate.", "muted", wrap=True), 1)
        pick = IconButton("Select video", "folder")
        pick.clicked.connect(lambda: pick_video(self, state))
        self.empty.layout_.addWidget(pick)
        self.body.addWidget(self.empty)
        self.summary = make_label("", "h2", wrap=True)
        self.body.addWidget(self.summary)

        row = ResponsiveRow(860, 18)
        left, right = QWidget(), QWidget()
        lv, rv = QVBoxLayout(left), QVBoxLayout(right)
        for v in (lv, rv):
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(18)

        # --- duration card -------------------------------------------------
        dur = Card(spacing=14)
        dur.layout_.addWidget(make_label("Length of each part", "h2"))
        fields = QHBoxLayout()
        fields.setSpacing(10)
        self.f_h, self.f_m, self.f_s = DurationField("Hours", 99), DurationField("Minutes", 59), DurationField("Seconds", 59)
        for i, f in enumerate((self.f_h, self.f_m, self.f_s)):
            if i:
                fields.addWidget(make_label(":", "h2"), 0, Qt.AlignmentFlag.AlignBottom)
            fields.addWidget(f, 1)
            f.valueChanged.connect(self._on_fields)
        dur.layout_.addLayout(fields)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chips: list[tuple[IconButton, int]] = []
        for label, secs in PRESETS:
            chip = IconButton(label, variant="chip")
            chip.setCheckable(True)
            chip.setToolTip(f"Split every {label}")
            chip.clicked.connect(lambda _=False, s=secs: self._apply_preset(s))
            chips.addWidget(chip)
            self.chips.append((chip, secs))
        chips.addStretch(1)
        dur.layout_.addLayout(chips)
        self.validation = make_label("", "error", wrap=True)
        dur.layout_.addWidget(self.validation)
        lv.addWidget(dur)

        # --- mode card -----------------------------------------------------
        mode = Card(spacing=8)
        mode.layout_.addWidget(make_label("Splitting mode", "h2"))
        self.r_fast = QRadioButton("Fast: stream copy (recommended)")
        self.r_fast.setToolTip("No re-encoding: very fast and no quality loss")
        mode.layout_.addWidget(self.r_fast)
        mode.layout_.addWidget(make_label(
            "Lightning fast with zero quality loss. Cuts can only happen on keyframes, so a part may run a few "
            "seconds longer than requested.", "muted", wrap=True))
        self.r_acc = QRadioButton("Accurate: re-encode")
        self.r_acc.setToolTip("Re-encodes the video so every part has exactly the requested length")
        mode.layout_.addWidget(self.r_acc)
        mode.layout_.addWidget(make_label(
            "Parts are exactly the requested length, but this is much slower and re-encodes the video "
            "(H.264, high quality). Needs more free disk space.", "muted", wrap=True))
        group = QButtonGroup(self)
        group.addButton(self.r_fast)
        group.addButton(self.r_acc)
        self.r_fast.toggled.connect(self._on_mode)
        lv.addWidget(mode)
        lv.addStretch(1)

        # --- estimate card -------------------------------------------------
        est = Card(spacing=12)
        est.layout_.addWidget(make_label("Estimate", "h2"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)
        self.e_movie, self.e_each, self.e_parts, self.e_last = (make_label("-", "stat") for _ in range(4))
        for i, (cap, lab) in enumerate([("Movie length", self.e_movie), ("Each part", self.e_each),
                                        ("Expected parts", self.e_parts), ("Last part", self.e_last)]):
            cell = QVBoxLayout()
            cell.setSpacing(0)
            cell.addWidget(lab)
            cell.addWidget(make_label(cap.upper(), "caption"))
            grid.addLayout(cell, i // 2, i % 2)
        est.layout_.addLayout(grid)
        self.est_note = make_label("", "warning", wrap=True)
        est.layout_.addWidget(self.est_note)
        rv.addWidget(est)

        # --- output card ---------------------------------------------------
        out = Card(spacing=10)
        out.layout_.addWidget(make_label("Output", "h2"))
        out.layout_.addWidget(make_label("SAVE LOCATION", "caption"))
        loc = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        self.out_edit.setToolTip("Parent folder. A sub-folder named after the movie is created automatically.")
        browse = IconButton("Browse…", "folder")
        browse.clicked.connect(self._browse_out)
        loc.addWidget(self.out_edit, 1)
        loc.addWidget(browse)
        out.layout_.addLayout(loc)
        out.layout_.addWidget(make_label("PARTS WILL BE SAVED IN", "caption"))
        self.final_dir = make_label("-", "mono", wrap=True)
        self.final_dir.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        out.layout_.addWidget(self.final_dir)
        self.example = make_label("", "muted", wrap=True)
        out.layout_.addWidget(self.example)
        acts = QHBoxLayout()
        self.copy_btn = IconButton("Copy path", "copy", size=16)
        self.copy_btn.clicked.connect(self._copy_path)
        self.open_btn = IconButton("Open folder", "folder", size=16)
        self.open_btn.clicked.connect(self._open_out)
        acts.addWidget(self.copy_btn)
        acts.addWidget(self.open_btn)
        acts.addStretch(1)
        out.layout_.addLayout(acts)
        self.open_after = QCheckBox("Open the output folder when finished")
        self.open_after.setChecked(bool(state.settings.get("open_folder_after")))
        self.open_after.toggled.connect(lambda v: state.settings.set("open_folder_after", bool(v)))
        out.layout_.addWidget(self.open_after)
        rv.addWidget(out)
        rv.addStretch(1)
        row.add(left, 1)
        row.add(right, 1)
        self.body.addWidget(row)

        # --- actions -------------------------------------------------------
        actions = QHBoxLayout()
        reset = IconButton("Reset", "refresh", "muted", "ghost")
        reset.setToolTip("Reset duration and mode (Ctrl+R also clears the video)")
        reset.clicked.connect(state.reset_split_settings)
        self.start_btn = IconButton("Start Splitting", "play", "white", "primary")
        self.start_btn.setToolTip("Start (Ctrl+Enter)")
        self.start_btn.clicked.connect(self.start)
        actions.addWidget(reset)
        actions.addStretch(1)
        actions.addWidget(self.start_btn)
        self.body.addLayout(actions)
        self.body.addStretch(1)

        for sig in (state.videoChanged, state.splitSettingsChanged, state.busyChanged, state.toolsChanged):
            sig.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------ input handling
    def _on_fields(self) -> None:
        if self._syncing:
            return
        self.state.set_segment_seconds(hms_to_seconds(self.f_h.value(), self.f_m.value(), self.f_s.value()))

    def _apply_preset(self, seconds: int) -> None:
        self.state.set_segment_seconds(seconds)

    def _on_mode(self) -> None:
        if not self._syncing:
            self.state.set_accurate(self.r_acc.isChecked())

    def _browse_out(self) -> None:
        folder = pick_folder(self, str(self.state.out_root))
        if folder:
            self.state.set_out_root(folder)

    def _copy_path(self) -> None:
        folder = self.state.output_dir() or self.state.out_root
        copy_text(str(folder), "Output folder path copied")

    def _open_out(self) -> None:
        for candidate in (self.state.output_dir(), self.state.out_root):
            if candidate and candidate.exists():
                open_folder(candidate)
                return
        copy_text("", "The folder does not exist yet. It is created automatically when splitting starts.")

    # ------------------------------------------------------------------ display
    def refresh(self) -> None:
        s = self.state
        self._syncing = True
        h, m, sec = split_hms(s.segment_seconds)
        for field, value in ((self.f_h, h), (self.f_m, m), (self.f_s, sec)):
            if field.value() != value and not field.edit.hasFocus():
                field.setValue(value)
        self.r_acc.setChecked(s.accurate)
        self.r_fast.setChecked(not s.accurate)
        for chip, secs in self.chips:
            chip.setChecked(secs == s.segment_seconds)
        self._syncing = False

        video = s.video
        self.empty.setVisible(video is None)
        self.summary.setVisible(video is not None)
        self.out_edit.setText(str(s.out_root))
        self.validation.setText("")
        self.est_note.setText("")
        ok = False
        if video is None:
            for lab in (self.e_movie, self.e_each, self.e_parts, self.e_last):
                lab.setText("-")
            self.final_dir.setText(elide(str(s.out_root), 70) + "  (select a video first)")
            self.example.setText("")
        else:
            self.summary.setText(f"{video.filename}   ·   {format_hms(video.duration)}   ·   {human_size(video.size_bytes)}")
            error = validate_segment(video.duration, s.segment_seconds)
            self.e_movie.setText(format_hms(video.duration))
            self.e_each.setText(format_hms(s.segment_seconds))
            final = s.output_dir()
            self.final_dir.setText(str(final))
            ext = output_extension(video.ext)
            stem = sanitize_name(video.stem)
            if error:
                self.validation.setText(error)
                self.e_parts.setText("-")
                self.e_last.setText("-")
                self.example.setText("")
            else:
                plan = plan_split(video.duration, s.segment_seconds)
                self.e_parts.setText(str(plan.part_count))
                self.e_last.setText(format_hms(plan.last_part_duration))
                first, last = part_filename(stem, 1, ext), part_filename(stem, plan.part_count, ext)
                self.example.setText(f"Files: {first}" + (f"  …  {last}" if plan.part_count > 1 else ""))
                notes = []
                if s.segment_seconds >= video.duration:
                    notes.append("The part length is not shorter than the movie, so only 1 part will be created.")
                if plan.part_count > 500:
                    notes.append(f"This will create {plan.part_count} parts. Consider a longer duration.")
                if not s.accurate and plan.part_count > 1:
                    notes.append("Fast mode cuts on keyframes, so parts may differ slightly from the exact length.")
                if ext.lower() != video.ext.lower():
                    notes.append(f"{video.ext} cannot be split directly, so parts will be saved as {ext}.")
                self.est_note.setText("\n".join(notes))
                set_role(self.est_note, "warning")
                ok = True
        if s.segment_seconds <= 0:
            self.validation.setText("Split duration must be greater than zero.")
        self.start_btn.setEnabled(ok and video is not None and not s.busy)
        self.start_btn.setText("Split in progress…" if s.busy else "Start Splitting")

    # ------------------------------------------------------------------ start
    def start(self) -> None:
        s = self.state
        if s.busy:
            return
        if s.tools is None:
            FFmpegSetupDialog(self.window(), s).exec()
            return
        video = s.video
        if video is None:
            s.navigate.emit(PAGE_VIDEO)
            return
        error = validate_segment(video.duration, s.segment_seconds)
        if error:
            show_error(self, "Invalid duration", error)
            return
        if not video.path.exists():
            show_error(self, "File not found", f"The source video is no longer available:\n{video.path}")
            return

        stem, ext = sanitize_name(video.stem), output_extension(video.ext)
        out_dir = s.output_dir()
        assert out_dir is not None
        overwrite = False
        existing = find_existing_parts(out_dir, stem, ext)
        if existing:                                     # never overwrite silently
            choice = ask_overwrite(self, out_dir, len(existing))
            if choice == "cancel":
                return
            if choice == "new":
                out_dir = unique_output_dir(s.out_root, stem)
            else:
                overwrite = True
        elif out_dir.exists() and any(out_dir.iterdir()):
            log.info("Output folder %s already has other files; they are left untouched", out_dir)

        try:                                             # fail early with a clear permission message
            out_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            show_error(self, "Permission denied", f"You do not have permission to write to:\n{out_dir}\n\nChoose another output location.")
            return
        except OSError as exc:
            show_error(self, "Cannot create folder", f"Could not create the output folder:\n{out_dir}\n\n{exc}")
            return

        needed = video.size_bytes
        free = free_space(out_dir)
        if free is not None and free < needed * (1.03 if not s.accurate else 1.0):
            note = "" if not s.accurate else "\n(Accurate mode output size can only be estimated roughly.)"
            if not confirm(self, "Not enough free disk space?",
                           f"The output drive has {human_size(free)} free, but about {human_size(needed)} is needed.{note}\n\n"
                           "Continue anyway?", "Continue", "Cancel", icon=QMessageBox.Icon.Warning):
                return

        count = estimate_part_count(video.duration, s.segment_seconds)
        if s.settings.get("confirm_before_start"):
            text = (f"Split “{video.filename}” into about {count} part(s) of {format_human(s.segment_seconds)} each?\n\n"
                    f"Mode: {'Accurate (re-encode, slower)' if s.accurate else 'Fast (stream copy)'}\n"
                    f"Folder: {out_dir}")
            if not confirm(self, "Start splitting?", text, "Start", "Cancel"):
                return

        job = SplitJob(info=video, out_dir=out_dir, stem=stem, out_ext=ext, segment_seconds=float(s.segment_seconds),
                       accurate=s.accurate, overwrite=overwrite, expected_parts=count)
        s.startJob.emit(job)
        s.navigate.emit(PAGE_PROGRESS)
