"""
Custom createsuperuser command that creates Superuser instances
in the 'superusers' table instead of the 'customers' table.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core import exceptions
from django.db import DEFAULT_DB_ALIAS
from django.contrib.auth import password_validation
from accounts.models import Superuser


class Command(BaseCommand):
    help = 'Used to create a superuser in the superusers table.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = Superuser

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            dest='username', default=None,
            help='Specifies the username for the superuser.',
        )
        parser.add_argument(
            '--email',
            dest='email', default=None,
            help='Specifies the email address for the superuser.',
        )
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive',
            help=(
                'Tells Django to NOT prompt the user for input of any kind. '
                'You must use --username with --noinput, and requires '
                'superusers created with --noinput to not have a usable '
                'password.'
            ),
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )

    def execute(self, *args, **options):
        self.stdin = options.get('stdin', self.stdin)  # Used for testing
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        """Handle the command execution."""
        username = options['username']
        email = options.get('email')
        database = options['database']
        user_data = {}

        # Validate input if --noinput mode
        if not options['interactive']:
            try:
                if not username:
                    raise CommandError("You must use --username with --noinput.")
                username = self.UserModel.normalize_username(username)

                user_data['username'] = username
                if email:
                    user_data['email'] = email
                else:
                    user_data['email'] = ''

                # Validate that the username is not already taken.
                if self.UserModel._default_manager.db_manager(database).filter(username=username).exists():
                    raise CommandError("Error: That username is already taken.")

                # Validate that the email is not already taken.
                if email and self.UserModel._default_manager.db_manager(database).filter(email=email).exists():
                    raise CommandError("Error: That email is already taken.")

            except exceptions.ValidationError as e:
                raise CommandError('; '.join(e.messages))

        else:
            # Prompt for username/email/password.  Pass username and email to an
            # existing user, or create a new user if that's allowed.
            username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)
            username = self._get_input_data(self.UserModel, username_field, username, 'username')
            user_data[self.UserModel.USERNAME_FIELD] = username
            fake_user_data = {}
            if username:
                fake_user_data[self.UserModel.USERNAME_FIELD] = username
                try:
                    self.UserModel._default_manager.db_manager(database).get(**fake_user_data)
                except self.UserModel.DoesNotExist:
                    pass
                else:
                    raise CommandError("Error: That %s is already taken." % username_field.verbose_name)

            if email:
                user_data['email'] = email
            else:
                user_data['email'] = self._get_input_data(self.UserModel, self.UserModel._meta.get_field('email'), None, 'email address')

            # Check if email is already taken
            if user_data['email'] and self.UserModel._default_manager.db_manager(database).filter(email=user_data['email']).exists():
                raise CommandError("Error: That email is already taken.")

            # Prompt for required fields.
            for field_name in self.UserModel.REQUIRED_FIELDS:
                field = self.UserModel._meta.get_field(field_name)
                user_data[field_name] = options.get(field_name)
                while user_data[field_name] is None:
                    user_data[field_name] = self._get_input_data(self.UserModel, field, None, field.verbose_name)

        # Get password
        password = None
        if not options['interactive']:
            # Non-interactive mode: no password (or unusable password)
            password = self.UserModel.objects.make_random_password()
            self.stdout.write(
                self.style.WARNING('Superuser created with unusable password. Use --password to set a password.')
            )
        else:
            # Interactive mode: get password
            password = self._get_password()

        user_data['password'] = password
        # is_superuser and is_staff will be set automatically by Superuser.save()
        # but we set them explicitly here for clarity
        user_data['is_superuser'] = True
        user_data['is_staff'] = True
        user_data['is_active'] = True

        superuser = self.UserModel._default_manager.db_manager(database).create_user(**user_data)

        if options['verbosity'] >= 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{superuser.username}" created successfully in "superusers" table.'
                )
            )

    def _get_input_data(self, model, field, default, prompt):
        """
        Get input data from user, or use default.
        
        Args:
            model: The user model class
            field: The field object
            default: Default value if user leaves blank
            prompt: Prompt text to display
            
        Returns:
            str: User input or default value
        """
        raw_value = input('%s%s: ' % (
            'Enter %s' % prompt,
            ' (leave blank to use \'%s\')' % default if default else '',
        ))
        if default and raw_value == '':
            raw_value = default
        return raw_value

    def _get_password(self):
        """
        Prompt for password from the user with validation.
        
        Returns:
            str: Validated password
        """
        password = None
        while password is None:
            password = self.get_pass_input('Password: ')
            password2 = self.get_pass_input('Password (again): ')
            if password != password2:
                self.stdout.write(self.style.ERROR('Error: Your passwords didn\'t match.'))
                password = None
                continue
            if password.strip() == '':
                self.stdout.write(self.style.ERROR('Error: Blank passwords aren\'t allowed.'))
                password = None
                continue
            # Validate the password
            try:
                password_validation.validate_password(password, self.UserModel(**{self.UserModel.USERNAME_FIELD: 'dummy'}))
            except exceptions.ValidationError as e:
                self.stdout.write(self.style.ERROR('Password validation errors:'))
                for error in e.messages:
                    self.stdout.write(self.style.ERROR('  - %s' % error))
                password = None
        return password

    def get_pass_input(self, prompt='Password: '):
        """
        Get password from user input, hiding it.
        
        Args:
            prompt: Prompt text to display
            
        Returns:
            str: Password entered by user
        """
        import getpass
        return getpass.getpass(prompt=prompt)

