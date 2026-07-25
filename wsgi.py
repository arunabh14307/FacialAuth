from app import app

class FixEmptyPathMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        if not environ.get('PATH_INFO'):
            environ['PATH_INFO'] = '/'
        return self.app(environ, start_response)

application = FixEmptyPathMiddleware(app)

if __name__ == '__main__':
    app.run()
