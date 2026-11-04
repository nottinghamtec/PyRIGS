import re
import uuid
from collections import Counter

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from reversion import revisions as reversion

from RIGS.models import Profile, ContactableManager
from versioning.versioning import RevisionMixin


class AssetCategory(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        verbose_name = "Asset Category"
        verbose_name_plural = "Asset Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AssetStatus(models.Model):
    name = models.CharField(max_length=80)
    should_show = models.BooleanField(default=True, help_text="Should this be shown by default in the asset list.")
    display_class = models.CharField(
        max_length=80,
        blank=True,
        help_text="HTML class to be appended to alter display of assets with this status, such as in the list.",
    )

    class Meta:
        verbose_name = "Asset Status"
        verbose_name_plural = "Asset Statuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


@reversion.register
class Supplier(models.Model, RevisionMixin):
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=15, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")

    notes = models.TextField(blank=True, default="")

    objects = ContactableManager()

    class Meta:
        ordering = ["name"]

    def get_absolute_url(self):
        return reverse("supplier_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name


class Connector(models.Model):
    description = models.CharField(max_length=80)
    current_rating = models.DecimalField(decimal_places=2, max_digits=10, help_text="Amps")
    voltage_rating = models.IntegerField(help_text="Volts")
    num_pins = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.description


class CableTypeManager(models.Manager):
    def get_queryset(self):
        # A cable type is only ever shown by name, which needs both connectors
        return super().get_queryset().select_related("plug", "socket")


class CableType(models.Model):
    circuits = models.IntegerField(default=1)
    cores = models.IntegerField(default=3)
    plug = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name="plug")
    socket = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name="socket")

    objects = CableTypeManager()

    class Meta:
        ordering = ["plug", "socket", "-circuits"]
        constraints = [
            models.UniqueConstraint(
                fields=["plug", "socket", "circuits", "cores"], name="unique_plug_socket_circuits_cores"
            )
        ]

    def __str__(self):
        if self.plug and self.socket:
            return f"{self.plug.description} → {self.socket.description}"
        else:
            return "Unknown"

    def get_absolute_url(self):
        return reverse("cable_type_detail", kwargs={"pk": self.pk})


class AssetManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (
                Q(asset_id__exact=query.upper())
                | Q(description__icontains=query)
                | Q(serial_number__exact=query)
                | Q(nickname__icontains=query)
            )
            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


def get_available_asset_id(wanted_prefix=""):
    last_asset = Asset.objects.filter(asset_id_prefix=wanted_prefix).last()
    last_asset_id = last_asset.asset_id_number if last_asset else 0
    return wanted_prefix + str(last_asset_id + 1)


def validate_positive(value):
    if value < 0:
        raise ValidationError("A price cannot be negative")


@reversion.register
class Asset(models.Model, RevisionMixin):
    parent = models.ForeignKey(to="self", related_name="asset_parent", blank=True, null=True, on_delete=models.SET_NULL)
    asset_id = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=120)
    category = models.ForeignKey(to=AssetCategory, on_delete=models.CASCADE)
    status = models.ForeignKey(to=AssetStatus, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=150, blank=True)
    purchased_from = models.ForeignKey(
        to=Supplier, on_delete=models.SET_NULL, blank=True, null=True, related_name="assets"
    )
    date_acquired = models.DateField()
    date_sold = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(
        blank=True, null=True, decimal_places=2, max_digits=10, validators=[validate_positive]
    )
    replacement_cost = models.DecimalField(null=True, decimal_places=2, max_digits=10, validators=[validate_positive])
    comments = models.TextField(blank=True)
    nickname = models.CharField(max_length=120, blank=True)

    # Audit
    last_audited_at = models.DateTimeField(blank=True, null=True)
    last_audited_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, related_name="audited_by", blank=True, null=True
    )

    # Cable assets
    is_cable = models.BooleanField(default=False)
    cable_type = models.ForeignKey(to=CableType, blank=True, null=True, on_delete=models.SET_NULL)
    length = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True, help_text="m")
    csa = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True, help_text="mm²")

    # Hidden asset_id components
    # For example, if asset_id was "C1001" then asset_id_prefix would be "C" and number "1001"
    asset_id_prefix = models.CharField(max_length=8, default="")
    asset_id_number = models.IntegerField(default=1)

    reversion_perm = "assets.asset_finance"

    objects = AssetManager()

    class Meta:
        ordering = ["asset_id_prefix", "asset_id_number"]
        permissions = [("asset_finance", "Can see financial data for assets")]

    def __str__(self):
        return f"{self.asset_id} | {self.description}"

    def get_absolute_url(self):
        return reverse("asset_detail", kwargs={"pk": self.asset_id})

    def clean(self):
        errdict = {}
        if self.date_sold and self.date_acquired > self.date_sold:
            errdict["date_sold"] = ["Cannot sell an item before it is acquired"]

        if self.parent_id and self.pk:
            seen = set()
            ancestor = self.parent
            while ancestor is not None and ancestor.pk not in seen:
                if ancestor.pk == self.pk:
                    errdict["parent"] = ["That would make the asset its own ancestor, creating a circular parent chain"]
                    break
                seen.add(ancestor.pk)
                ancestor = ancestor.parent

        self.asset_id = self.asset_id.upper()
        asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", self.asset_id)
        if asset_search is None:
            errdict["asset_id"] = ["An Asset ID can only consist of letters and numbers, with a final number"]

        if self.is_cable:
            if not self.length or self.length <= 0:
                errdict["length"] = ["The length of a cable must be more than 0"]
            if not self.csa or self.csa <= 0:
                errdict["csa"] = ["The CSA of a cable must be more than 0"]
            if not self.cable_type:
                errdict["cable_type"] = ["A cable must have a type"]

        if errdict != {}:  # If there was an error when validation
            raise ValidationError(errdict)

    @property
    def activity_feed_string(self):
        return str(self)

    @property
    def display_id(self):
        return str(self.asset_id)

    @property
    def display_name(self):
        return f"{self.display_id} | {self.description}"

    @property
    def latest_pat_test(self):
        return self.pat_tests.order_by("-tested_at").first()

    @property
    def pat_status(self):
        if hasattr(self, "pat_last_tested"):
            return PATTestRecord.status_from(self.pat_last_tested, self.pat_last_passed, self.pat_next_due)
        return PATTestRecord.status_for(self.latest_pat_test)

    @property
    def pat_status_label(self):
        return PATTestRecord.STATUS_LABELS[self.pat_status]


PAT_UNIT_LABELS = {"ohm": "Ω", "Mohm": "MΩ", "deg": "°"}


def pat_unit(unit):
    return PAT_UNIT_LABELS.get(unit, unit)


def pat_value(value, unit):
    return f"{value} {pat_unit(unit)}".strip()


def pat_upload_path(instance, filename):
    return f"pat/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.sss"


class PATTestBatch(models.Model):
    file = models.FileField(upload_to=pat_upload_path)
    original_filename = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, db_index=True)
    machine_model = models.CharField(max_length=40, blank=True)
    machine_serial = models.CharField(max_length=40, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(Profile, null=True, on_delete=models.SET_NULL, related_name="pat_uploads")
    unmatched_asset_ids = models.JSONField(default=list, blank=True)
    conflicts = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.uploaded_at:%Y-%m-%d})"



class PATTestRecord(models.Model):
    NOT_TESTED = "not_tested"
    FAILED = "failed"
    OVERDUE = "overdue"
    IN_DATE = "in_date"
    STATUS_LABELS = {
        NOT_TESTED: "Never PAT tested",
        FAILED: "Failed PAT",
        OVERDUE: "PAT overdue",
        IN_DATE: "PAT in date",
    }

    batch = models.ForeignKey(PATTestBatch, on_delete=models.CASCADE, related_name="records")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="pat_tests")
    tested_at = models.DateTimeField()
    passed = models.BooleanField(null=True)
    operator = models.CharField(max_length=16, blank=True)
    comments = models.TextField(blank=True)
    next_full_test_date = models.DateField(null=True, blank=True)
    next_visual_test_date = models.DateField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-tested_at"]
        constraints = [models.UniqueConstraint(fields=["asset", "tested_at"], name="unique_pat_test_per_asset_time")]

    def __str__(self):
        return f"{self.asset.asset_id} {'passed' if self.passed else 'failed'} on {self.tested_at:%Y-%m-%d}"

    @classmethod
    def status_from(cls, tested_at, passed, next_full_test_date):
        if tested_at is None:
            return cls.NOT_TESTED
        if passed is False:
            return cls.FAILED
        if next_full_test_date and next_full_test_date < timezone.localdate():
            return cls.OVERDUE
        return cls.IN_DATE

    @classmethod
    def status_for(cls, record):
        if record is None:
            return cls.NOT_TESTED
        return cls.status_from(record.tested_at, record.passed, record.next_full_test_date)

    @property
    def status(self):
        return self.status_for(self)

    @staticmethod
    def describe_reading(item):
        measurements = item.get("measurements", [])
        if not measurements:
            return ""
        parts = []
        for index, m in enumerate(measurements):
            qualifier = item.get("qualifier", "") if index == len(measurements) - 1 else ""
            parts.append(f"{m['name']} {qualifier}{m['value']} {m['unit']}")
        return f" ({', '.join(parts)})"

    def expected_counts(self):
        """How many times the program says each kind of test should run"""
        counts = Counter()
        for step in self.details.get("program_steps", []):
            if step["kind"] not in ("Comment", "Visual check"):
                counts[step["kind"]] += step.get("repeats", 1)
        return counts

    def flagged(self):
        """Everything the tester marked as failed in this result, whatever its overall verdict was."""
        reasons = []
        visual = [check for check in self.details.get("visual_checks", []) if check["status"] == "FAIL"]
        if len(visual) == 1:
            reasons.append(f"Visual check failed: {visual[0]['kind']}{self.describe_reading(visual[0])}")
        elif visual:
            reasons.append(f"Visual checks failed: {', '.join(check['kind'] for check in visual)}")
        steps = self.details.get("steps", [])
        totals = Counter(step["kind"] for step in steps)
        expected = self.expected_counts()
        seen = Counter()
        for step in steps:
            seen[step["kind"]] += 1
            if step["status"] != "FAIL":
                continue
            of = max(totals[step["kind"]], expected[step["kind"]])
            repeat = f" [{seen[step['kind']]} of {of}]" if of > 1 else ""
            if step["kind"] == "Comment":
                reasons.append(f"Failed by the operator at the prompt '{step['text']}'{repeat}")
            else:
                reasons.append(f"{step['kind']} failed{self.describe_reading(step)}{repeat}")
        return reasons

    @property
    def failure_reasons(self):
        return self.flagged() if self.passed is not True else []

    @property
    def notes(self):
        notes = [self.comments] if self.comments else []
        flagged = self.flagged() if self.passed is True else []
        if flagged:
            notes.append(f"Recorded as a pass overall, but the tester also flagged: {'; '.join(flagged)}")
        return notes

    @property
    def program(self):
        return self.details.get("program", "")

    @staticmethod
    def describe_limit(program_step):
        if "limit" not in program_step:
            return ""
        operator = "≤" if program_step["limit_type"] == "max" else "≥"
        return f"{operator} {pat_value(program_step['limit'], program_step['unit'])}"

    @property
    def has_limits(self):
        return any("limit" in step for step in self.details.get("program_steps", []))

    def display_program(self):
        """What the test program defines, with a repeated cycle (like each connector of a Socapex) shown once"""
        items = []
        for step in self.details.get("program_steps", []):
            kind = step["kind"]
            if kind == "Visual check":
                continue
            if kind == "Comment":
                items.append({"text": f"Prompt: {step['text']}" if step.get("text") else "Prompt", "prompt": True})
                continue
            text = kind
            if step.get("repeats", 1) > 1:
                text += f" ×{step['repeats']}"
            if "voltage" in step:
                text += f" at {pat_value(step['voltage'], 'V')}"
            if "test_current" in step:
                text += f" at {pat_value(step['test_current'], 'mA')}, {pat_value(step['angle'], 'deg')}"
            limit = self.describe_limit(step)
            if limit:
                text += f", {limit}"
            items.append({"text": text, "prompt": False})
        texts = [item["text"] for item in items]
        for period in range(1, len(texts) // 2 + 1):
            if all(texts[i] == texts[i % period] for i in range(len(texts))):
                return {"items": items[:period], "sections": -(-len(texts) // period)}
        return {"items": items, "sections": 1}

    def display_visual_checks(self):
        return [
            {
                "kind": check["kind"],
                "status": check["status"],
                "reading": ", ".join(pat_value(m["value"], m["unit"]) for m in check.get("measurements", [])),
            }
            for check in self.details.get("visual_checks", [])
        ]

    def display_steps(self):
        """The recorded steps as rows to show, each lined up with the limit its program set for it"""
        steps = self.details.get("steps", [])
        expected = []
        for program_step in self.details.get("program_steps", []):
            if program_step["kind"] not in ("Comment", "Visual check"):
                expected += [program_step] * program_step.get("repeats", 1)
        totals = Counter(step["kind"] for step in steps if step["kind"] != "Comment")
        # the tester stops at a failure, so more can be expected than were run
        for kind, count in self.expected_counts().items():
            totals[kind] = max(totals[kind], count)
        # A prompt (like "Change Connector") splits the test into sections
        sections = sum(1 for step in steps if step["kind"] == "Comment") + 1
        seen = Counter()
        position = 0
        section = 0
        start_section = sections > 1
        rows = []
        for step in steps:
            if step["kind"] == "Comment":
                rows.append({"prompt": step["text"] or "Prompt", "status": step["status"]})
                start_section = True
                continue
            if start_section and sections > 1:
                section += 1
                rows.append({"section": f"Section {section} of {sections}"})
                start_section = False
            seen[step["kind"]] += 1
            limit = ""
            for index in range(position, len(expected)):
                if expected[index]["kind"] == step["kind"]:
                    limit = self.describe_limit(expected[index])
                    position = index + 1
                    break
            measurements = step.get("measurements", [])
            reading = ""
            if measurements:
                qualifier = f"{step['qualifier']} " if step.get("qualifier") else ""
                reading = qualifier + pat_value(measurements[-1]["value"], measurements[-1]["unit"])
            numbered = totals[step["kind"]] > 1 and not (sections > 1 and totals[step["kind"]] == sections)
            rows.append(
                {
                    "prompt": "",
                    "section": "",
                    "kind": step["kind"],
                    "repeat": f"{seen[step['kind']]} of {totals[step['kind']]}" if numbered else "",
                    "reading": reading,
                    "setup": ", ".join(pat_value(m["value"], m["unit"]) for m in measurements[:-1]),
                    "limit": limit,
                    "status": step["status"],
                    "flags": step.get("flags", 0),
                }
            )
        return rows

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]
