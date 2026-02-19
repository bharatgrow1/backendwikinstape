from django.db import models


class PersonalLoan(models.Model):
    EMPLOYMENT_CHOICES = (
        ("salaried", "Salaried"),
        ("self-employed", "Self Employed"),
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10)
    email = models.EmailField()
    pan_number = models.CharField(max_length=10)
    dob = models.DateField()
    credit_score = models.IntegerField(null=True, blank=True)
    pincode = models.CharField(max_length=6)

    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES)
    employer_name = models.CharField(max_length=255)
    office_pin_code = models.CharField(max_length=6)
    monthly_income = models.IntegerField()

    external_lead_id = models.CharField(max_length=100, null=True, blank=True)
    external_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} - {self.mobile}"
