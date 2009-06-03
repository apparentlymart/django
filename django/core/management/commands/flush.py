from optparse import make_option

from django.conf import settings
from django.db import connections, transaction, models
from django.core.management import call_command
from django.core.management.base import NoArgsCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import sql_flush, emit_post_sync_signal
from django.utils.importlib import import_module



class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
            default='', help='Nominates a database to flush.  Defaults to '
                'flushing all databases.'),
    )
    help = "Executes ``sqlflush`` on the current database."

    def handle_noargs(self, **options):
        if not options['database']:
            dbs = connections.all()
        else:
            dbs = [options['database']]

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive')

        self.style = no_style()

            # Import the 'management' module within each installed app, to register
            # dispatcher events.
            for app_name in settings.INSTALLED_APPS:
                try:
                    import_module('.management', app_name)
                except ImportError:
                    pass

            sql_list = sql_flush(self.style, connection, only_django=True)

            if interactive:
                confirm = raw_input("""You have requested a flush of the database.
    This will IRREVERSIBLY DESTROY all data currently in the %r database,
    and return each table to the state it was in after syncdb.
    Are you sure you want to do this?

        Type 'yes' to continue, or 'no' to cancel: """ % connection.settings_dict['DATABASE_NAME'])
            else:
                confirm = 'yes'

            if confirm == 'yes':
                try:
                    cursor = connection.cursor()
                    for sql in sql_list:
                        cursor.execute(sql)
                except Exception, e:
                    transaction.rollback_unless_managed()
                    raise CommandError("""Database %s couldn't be flushed. Possible reasons:
          * The database isn't running or isn't configured correctly.
          * At least one of the expected database tables doesn't exist.
          * The SQL was invalid.
        Hint: Look at the output of 'django-admin.py sqlflush'. That's the SQL this command wasn't able to run.
        The full error: %s""" % (connection.settings_dict.DATABASE_NAME, e))
                transaction.commit_unless_managed()

                # Emit the post sync signal. This allows individual
                # applications to respond as if the database had been
                # sync'd from scratch.
                emit_post_sync_signal(models.get_models(), verbosity, interactive, connection)

                # Reinstall the initial_data fixture.
                call_command('loaddata', 'initial_data', **options)

        for app_name in settings.INSTALLED_APPS:
            try:
                import_module('.management', app_name)
            except ImportError:
                pass

        for connection in dbs:

            # Import the 'management' module within each installed app, to register
            # dispatcher events.
            sql_list = sql_flush(self.style, connection, only_django=True)

            if interactive:
                confirm = raw_input("""You have requested a flush of the database.
    This will IRREVERSIBLY DESTROY all data currently in the %r database,
    and return each table to the state it was in after syncdb.
    Are you sure you want to do this?

        Type 'yes' to continue, or 'no' to cancel: """ % connection.settings_dict['DATABASE_NAME'])
            else:
                confirm = 'yes'

            if confirm == 'yes':
                try:
                    cursor = connection.cursor()
                    for sql in sql_list:
                        cursor.execute(sql)
                except Exception, e:
                    transaction.rollback_unless_managed()
                    raise CommandError("""Database %s couldn't be flushed. Possible reasons:
          * The database isn't running or isn't configured correctly.
          * At least one of the expected database tables doesn't exist.
          * The SQL was invalid.
        Hint: Look at the output of 'django-admin.py sqlflush'. That's the SQL this command wasn't able to run.
        The full error: %s""" % (connection.settings_dict.DATABASE_NAME, e))
                transaction.commit_unless_managed()

                # Emit the post sync signal. This allows individual
                # applications to respond as if the database had been
                # sync'd from scratch.
                emit_post_sync_signal(models.get_models(), verbosity, interactive, connection)

                # Reinstall the initial_data fixture.
                call_command('loaddata', 'initial_data', **options)

            else:
                print "Flush cancelled."
