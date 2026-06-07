from django.db import models


class CarMake(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # Any other fields you would like to include in a car make

    def __str__(self):
        return self.name


class CarModel(models.Model):
    class TYPE_CHOICES(models.TextChoices):
        SEDAN = 'Sedan', 'Sedan'
        SUV = 'SUV', 'SUV'
        WAGON = 'Wagon', 'Wagon'

    # Many-to-one relationship to CarMake model (One car make can have many car models)
    car_make = models.ForeignKey(CarMake, on_delete=models.CASCADE)
    # Dealer ID (IntegerField) refers to a dealer created in Cloudant database
    dealer_id = models.IntegerField()
    name = models.CharField(max_length=100)
    # Type (CharField with a choices argument to provide limited choices such as Sedan, SUV, and Wagon)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    # Year (IntegerField)
    year = models.IntegerField()
    # Any other fields you would like to include in a car model

    def __str__(self):
        return f"{self.car_make.name} {self.name}"