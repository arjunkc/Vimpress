blog_username = 'arjunwordpress'
blog_password = 'banned123'
blog_url='https://www.math.utah.edu/~arjunkc/wordpress/xmlrpc.php'

# sets the handler to wp. See https://codex.wordpress.org/XML-RPC_WordPress_API
handler = xmlrpclib.ServerProxy(blog_url).wp

