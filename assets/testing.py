from django.db import models

from . import models as am


class Test(models.Model):
    item = models.ForeignKey(to=am.Asset, on_delete=models.CASCADE)
    date = models.DateField()
    tested_by = models.ForeignKey(to='RIGS.Profile', on_delete=models.CASCADE)


class ElectricalTest(Test):
    visual = models.BooleanField()
    remarks = models.TextField()


class CableTest(ElectricalTest):
    # Should contain X circuit tests, where X is determined by circuits as per cable type
    pass


class CircuitTest(models.Model):
    test = models.ForeignKey(to=CableTest, on_delete=models.CASCADE)
    continuity = models.DecimalField(help_text='Ω')
    insulation_resistance = models.DecimalField(help_text='MΩ')


class TestRequirement(models.Model):
    item = models.ForeignKey(to=am.Asset, on_delete=models.CASCADE)
    test_type = models.ForeignKey(to=Test, on_delete=models.CASCADE)
    period = models.IntegerField() # X months


class CableTestForm(forms.ModelForm):
    class Meta
        model = CableTest


class CircuitTest(forms.ModelForm):
    class Meta:
        model = Choice
        exclude = ('test',)
