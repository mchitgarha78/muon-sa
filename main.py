from api import app, add_user, remove_user



if __name__ == '__main__':
    # TODO: WSGI or uvicorn
    app.run(debug=True)
    