from django import forms

from events.models import Bout


def weight_class_choices():
    values = (
        Bout.objects.exclude(weight_class="")
        .order_by("weight_class")
        .values_list("weight_class", flat=True)
        .distinct()
    )
    return [("", "All weight classes")] + [(value, value) for value in values]


class EventFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    weight_class = forms.ChoiceField(required=False, label="Weight class")
    date_from = forms.DateField(
        required=False, label="From", widget=forms.DateInput(attrs={"type": "date"})
    )
    date_to = forms.DateField(
        required=False, label="To", widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["weight_class"].choices = weight_class_choices()
