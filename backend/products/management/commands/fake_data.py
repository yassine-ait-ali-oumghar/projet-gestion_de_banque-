from django.core.management.base import BaseCommand
from faker import Faker
from products.models import Category, Product
import random

class Command(BaseCommand):
    help = 'Génère des données fictives pour les produits'

    def handle(self, *args, **options):
        faker = Faker('fr_FR')
        categories = []

        # Créer 5 catégories
        for _ in range(5):
            name = faker.word().capitalize()
            slug = faker.slug()
            categorie = Category.objects.create(name=name, slug=slug)
            categories.append(categorie)
            self.stdout.write(f'Catégorie créée avec succès: {name}')

        # Créer 8 produits
        for i in range(8):
            Product.objects.create(
                name=' '.join(faker.words(3)).capitalize(),
                description=faker.text(),
                price=round(random.uniform(1000, 8000), 2),
                category=random.choice(categories),
                stock=random.randint(10, 100),
            )
            self.stdout.write(f'Produit {i+1} créé avec succès')