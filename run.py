from app import init_app, app

if __name__ == '__main__':
    init_app()
    app.run(debug=True, host='0.0.0.0', port=5000)