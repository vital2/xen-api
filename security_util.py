# Utility class which provides security decorators to xen_api_exposer
import psycopg2
import ConfigParser


config = ConfigParser.ConfigParser()

# TODO change this to a common config file on a shared location
config.read("/home/vital/config.ini")


def expose(func):
    """ Decorator to mark RPC exposed functions """
    func.exposed = True
    return func


def requires_user_privilege(func):
    """ Decorator to make user privilege required to access the method """
    func.user_privilege_required = True
    return func


def requires_authentication_only(func):
    """ Decorator to mark that only authentication is required to access the method """
    func.auth_required = True
    return func


def requires_admin_privilege(func):
    """ Decorator to mark that admin privilege is required to access the method """
    func.admin_privilege_required = True
    return func


def is_exposed(func):
    """ Checks if the function is RPC exposed """
    return getattr(func, 'exposed', False)


# TODO this method should call out to another Authenticator class to make this generic
def is_authorized(func, user, passwd):
    """ Checks if user is valid and if user can  perform the action specified """

    print config.get("Database", "VITAL_DB_NAME")+config.get("Database", "VITAL_DB_PORT")

    conn = psycopg2.connect(database=config.get("Database", "VITAL_DB_NAME"),
                            user=config.get("Database", "VITAL_DB_USER"),
                            password=config.get("Database", "VITAL_DB_PWD"),
                            host=config.get("Database", "VITAL_DB_HOST"),
                            port=config.get("Database", "VITAL_DB_PORT"))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT password, is_admin, is_faculty from vital_vlab_user where email='" + user + "' and is_active=true")

        rows = cur.fetchall()
        if len(rows) == 0:
            raise Exception('access to method "%s" with credentials provided is restricted' % func)

        row = rows[0]
        if not passwd == row[0]:
            raise Exception('access to method "%s" with credentials provided is restricted' % func)

        if getattr(func, 'admin_privilege_required', False):
            if not row[1]:
                raise Exception('access to method "%s" with credentials provided is restricted' % func)
        elif getattr(func, 'user_privilege_required', False):
            # check if user has access to VMs
            pass
        elif getattr(func, 'auth_required', False):
            # user already authenticated
            pass
        else:
            # all operations need to be authenticated
            raise Exception('access to method is not supported')
    finally:
        conn.close()
