from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from reversion import revisions as reversion
from versioning.versioning import RevisionMixin

from RIGS.validators import validate_url


@reversion.register
class RiskAssessment(models.Model, RevisionMixin):
    SMALL = (0, 'Small')
    MEDIUM = (1, 'Medium')
    LARGE = (2, 'Large')
    SIZES = (SMALL, MEDIUM, LARGE)

    event = models.OneToOneField('Event', on_delete=models.CASCADE)
    # General
    nonstandard_equipment = models.BooleanField(help_text="Does the event require any hired in equipment or use of equipment that is not covered by <a href='https://nottinghamtec.sharepoint.com/:f:/g/HealthAndSafety/Eo4xED_DrqFFsfYIjKzMZIIB6Gm_ZfR-a8l84RnzxtBjrA?e=Bf0Haw'>"
                                                          "TEC's standard risk assessments and method statements?</a>")
    nonstandard_use = models.BooleanField(help_text="Are TEC using their equipment in a way that is abnormal?<br><small>i.e. Not covered by TECs standard health and safety documentation</small>")
    contractors = models.BooleanField(help_text="Are you using any external contractors?<br><small>i.e. Freelancers/Crewing Companies</small>")
    other_companies = models.BooleanField(help_text="Are TEC working with any other companies on site?<br><small>e.g. TEC is providing the lighting while another company does sound</small>")
    crew_fatigue = models.BooleanField(help_text="Is crew fatigue likely to be a risk at any point during this event?")
    general_notes = models.TextField(blank=True, default='', help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")

    # Power
    big_power = models.BooleanField(help_text="Does the event require larger power supplies than 13A or 16A single phase wall sockets, or draw more than 20A total current?")
    power_mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='power_mic', blank=True, null=True,
                                  verbose_name="Power MIC", on_delete=models.CASCADE, help_text="Who is the Power MIC? (if yes to the above question, this person <em>must</em> be a Power Technician or Power Supervisor)")
    outside = models.BooleanField(help_text="Is the event outdoors?")
    generators = models.BooleanField(help_text="Will generators be used?")
    other_companies_power = models.BooleanField(help_text="Will TEC be supplying power to any other companies?")
    nonstandard_equipment_power = models.BooleanField(help_text="Does the power plan require the use of any power equipment (distros, dimmers, motor controllers, etc.) that does not belong to TEC?")
    multiple_electrical_environments = models.BooleanField(help_text="Will the electrical installation occupy more than one electrical environment?")
    power_notes = models.TextField(blank=True, default='', help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")
    power_plan = models.URLField(blank=True, default='', help_text="Upload your power plan to the <a href='https://nottinghamtec.sharepoint.com/'>Sharepoint</a> and submit a link", validators=[validate_url])

    # Sound
    noise_monitoring = models.BooleanField(help_text="Does the event require noise monitoring or any non-standard procedures in order to comply with health and safety legislation or site rules?")
    sound_notes = models.TextField(blank=True, default='', help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")

    # Site
    known_venue = models.BooleanField(help_text="Is this venue new to you (the MIC) or new to TEC?")
    safe_loading = models.BooleanField(help_text="Are there any issues preventing a safe load in or out? (e.g. sufficient lighting, flat, not in a crowded area etc.)")
    safe_storage = models.BooleanField(help_text="Are there any problems with safe and secure equipment storage?")
    area_outside_of_control = models.BooleanField(help_text="Is any part of the work area out of TEC's direct control or openly accessible during the build or breakdown period?")
    barrier_required = models.BooleanField(help_text="Is there a requirement for TEC to provide any barrier for security or protection of persons/equipment?")
    nonstandard_emergency_procedure = models.BooleanField(help_text="Does the emergency procedure for the event differ from TEC's standard procedures?")

    # Structures
    special_structures = models.BooleanField(help_text="Does the event require use of winch stands, motors, MPT Towers, or staging?")
    suspended_structures = models.BooleanField(help_text="Are any structures (excluding projector screens and IWBs) being suspended from TEC's structures?")
    persons_responsible_structures = models.TextField(blank=True, default='', help_text="Who are the persons on site responsible for their use?")
    rigging_plan = models.URLField(blank=True, default='', help_text="Upload your rigging plan to the <a href='https://nottinghamtec.sharepoint.com/'>Sharepoint</a> and submit a link", validators=[validate_url])

    # Blimey that was a lot of options

    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    verbose_name="Reviewer", on_delete=models.CASCADE)

    supervisor_consulted = models.BooleanField(null=True)

    expected_values = {
        'nonstandard_equipment': False,
        'nonstandard_use': False,
        'contractors': False,
        'other_companies': False,
        'crew_fatigue': False,
        # 'big_power': False Doesn't require checking with a super either way
        'generators': False,
        'other_companies_power': False,
        'nonstandard_equipment_power': False,
        'multiple_electrical_environments': False,
        'noise_monitoring': False,
        'known_venue': False,
        'safe_loading': False,
        'safe_storage': False,
        'area_outside_of_control': False,
        'barrier_required': False,
        'nonstandard_emergency_procedure': False,
        'special_structures': False,
        'suspended_structures': False,
    }
    inverted_fields = {key: value for (key, value) in expected_values.items() if not value}.keys()

    def clean(self):
        # Check for idiots
        if not self.outside and self.generators:
            raise forms.ValidationError("Engage brain, please. <strong>No generators indoors!(!)</strong>")

    class Meta:
        ordering = ['event']
        permissions = [
            ('review_riskassessment', 'Can review Risk Assessments')
        ]

    @cached_property
    def fieldz(self):
        return [n.name for n in list(self._meta.get_fields()) if n.name != 'reviewed_at' and n.name != 'reviewed_by' and not n.is_relation and not n.auto_created]

    @property
    def event_size(self):
        # Confirm event size. Check all except generators, since generators entails outside
        if self.outside or self.other_companies_power or self.nonstandard_equipment_power or self.multiple_electrical_environments:
            return self.LARGE[0]
        elif self.big_power:
            return self.MEDIUM[0]
        else:
            return self.SMALL[0]

    def get_event_size_display(self):
        return self.SIZES[self.event_size][1] + " Event"

    @property
    def activity_feed_string(self):
        return str(self.event)

    @property
    def name(self):
        return str(self)

    def get_absolute_url(self):
        return reverse('ra_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f"{self.pk} | {self.event}"


@reversion.register(follow=['vehicles', 'crew'])
class EventChecklist(models.Model, RevisionMixin):
    event = models.ForeignKey('Event', related_name='checklists', on_delete=models.CASCADE)

    # General
    power_mic = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='checklists',
                                  verbose_name="Power MIC", on_delete=models.CASCADE, help_text="Who is the Power MIC?")
    venue = models.ForeignKey('Venue', on_delete=models.CASCADE)
    date = models.DateField()

    # Safety Checks
    safe_parking = models.BooleanField(blank=True, null=True, help_text="Vehicles parked safely?<br><small>(does not obstruct venue access)</small>")
    safe_packing = models.BooleanField(blank=True, null=True, help_text="Equipment packed away safely?<br><small>(including flightcases)</small>")
    exits = models.BooleanField(blank=True, null=True, help_text="Emergency exits clear?")
    trip_hazard = models.BooleanField(blank=True, null=True, help_text="Appropriate barriers around kit and cabling secured?")
    warning_signs = models.BooleanField(blank=True, help_text="Warning signs in place?<br><small>(strobe, smoke, power etc.)</small>")
    ear_plugs = models.BooleanField(blank=True, null=True, help_text="Ear plugs issued to crew where needed?")
    hs_location = models.CharField(blank=True, default='', max_length=255, help_text="Location of Safety Bag/Box")
    extinguishers_location = models.CharField(blank=True, default='', max_length=255, help_text="Location of fire extinguishers")

    # Small Electrical Checks
    rcds = models.BooleanField(blank=True, null=True, help_text="RCDs installed where needed and tested?")
    supply_test = models.BooleanField(blank=True, null=True, help_text="Electrical supplies tested?<br><small>(using socket tester)</small>")

    # Shared electrical checks
    earthing = models.BooleanField(blank=True, null=True, help_text="Equipment appropriately earthed?<br><small>(truss, stage, generators etc)</small>")
    pat = models.BooleanField(blank=True, null=True, help_text="All equipment in PAT period?")

    # Medium Electrical Checks
    source_rcd = models.BooleanField(blank=True, null=True, help_text="Source RCD protected?<br><small>(if cable is more than 3m long) </small>")
    labelling = models.BooleanField(blank=True, null=True, help_text="Appropriate and clear labelling on distribution and cabling?")
    # First Distro
    fd_voltage_l1 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L1-N", help_text="L1 - N")
    fd_voltage_l2 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L2-N", help_text="L2 - N")
    fd_voltage_l3 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L3-N", help_text="L3 - N")
    fd_phase_rotation = models.BooleanField(blank=True, null=True, verbose_name="Phase Rotation", help_text="Phase Rotation<br><small>(if required)</small>")
    fd_earth_fault = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2, verbose_name="Earth Fault Loop Impedance", help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    fd_pssc = models.IntegerField(blank=True, null=True, verbose_name="PSCC", help_text="Prospective Short Circuit Current")
    # Worst case points
    w1_description = models.CharField(blank=True, default='', max_length=255, help_text="Description")
    w1_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w1_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w1_earth_fault = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2, verbose_name="Earth Fault Loop Impedance", help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    w2_description = models.CharField(blank=True, default='', max_length=255, help_text="Description")
    w2_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w2_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w2_earth_fault = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2, verbose_name="Earth Fault Loop Impedance", help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    w3_description = models.CharField(blank=True, default='', max_length=255, help_text="Description")
    w3_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w3_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w3_earth_fault = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2, verbose_name="Earth Fault Loop Impedance", help_text="Earth Fault Loop Impedance (Z<small>S</small>)")

    all_rcds_tested = models.BooleanField(blank=True, null=True, help_text="All circuit RCDs tested?<br><small>(using test button)</small>")
    public_sockets_tested = models.BooleanField(blank=True, null=True, help_text="Public/Performer accessible circuits tested?<br><small>(using socket tester)</small>")

    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    verbose_name="Reviewer", on_delete=models.CASCADE)

    inverted_fields = []

    class Meta:
        ordering = ['event']
        permissions = [
            ('review_eventchecklist', 'Can review Event Checklists')
        ]

    @cached_property
    def fieldz(self):
        return [n.name for n in list(self._meta.get_fields()) if n.name != 'reviewed_at' and n.name != 'reviewed_by' and not n.is_relation and not n.auto_created]

    @property
    def activity_feed_string(self):
        return str(self.event)

    def get_absolute_url(self):
        return reverse('ec_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f"{self.pk} | {self.event}"


@reversion.register
class EventChecklistVehicle(models.Model, RevisionMixin):
    checklist = models.ForeignKey('EventChecklist', related_name='vehicles', blank=True, on_delete=models.CASCADE)
    vehicle = models.CharField(max_length=255)
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='vehicles', on_delete=models.CASCADE)

    reversion_hide = True

    def __str__(self):
        return f"{self.vehicle} driven by {self.driver}"


@reversion.register
class EventChecklistCrew(models.Model, RevisionMixin):
    checklist = models.ForeignKey('EventChecklist', related_name='crew', blank=True, on_delete=models.CASCADE)
    crewmember = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='crewed', on_delete=models.CASCADE)
    role = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()

    reversion_hide = True

    def clean(self):
        if self.start > self.end:
            raise ValidationError('Unless you\'ve invented time travel, crew can\'t finish before they have started.')

    def __str__(self):
        return f"{self.crewmember} ({self.role})"
