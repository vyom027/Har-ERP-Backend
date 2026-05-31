from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.operations.models import Operation, SubOperation

class Command(BaseCommand):
    help = 'Seed initial operations and sub-operations'

    def handle(self, *args, **kwargs):
        # 1. Create Superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Admin user created (admin/admin123)'))

        # 2. Seed Operations
        ops = [
            "Numbering", "Jati", "Front", "Marking", "Back", "Zipper", 
            "SM", "5th", "HT", "Belt", "Belt Elastic", "Belt Label & Lash", 
            "Bottom", "Bell Finish", "Bartake", "Loops", "Gaj", "Checking"
        ]

        for i, name in enumerate(ops, 1):
            op, created = Operation.objects.get_or_create(
                name=name,
                defaults={'display_order': i}
            )
            if created:
                self.stdout.write(f'Created operation: {name}')

        # 3. Seed Sub-Operations
        # SM -> yog, sit, inside
        sm_op = Operation.objects.get(name="SM")
        sm_op.has_sub_operations = True
        sm_op.save()
        
        sm_subs = ["yog", "sit", "inside"]
        for i, name in enumerate(sm_subs, 1):
            SubOperation.objects.get_or_create(
                operation=sm_op,
                name=name,
                defaults={'display_order': i}
            )

        # 5th -> sit, side, inside
        fifth_op = Operation.objects.get(name="5th")
        fifth_op.has_sub_operations = True
        fifth_op.save()
        
        fifth_subs = ["sit", "side", "inside"]
        for i, name in enumerate(fifth_subs, 1):
            SubOperation.objects.get_or_create(
                operation=fifth_op,
                name=name,
                defaults={'display_order': i}
            )

        self.stdout.write(self.style.SUCCESS('Seed data completed!'))
