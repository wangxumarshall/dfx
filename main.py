from app import create_app

# Create the Flask app instance using the application factory
app = create_app()

if __name__ == '__main__':
    # The host '0.0.0.0' makes the app accessible from other machines on the network.
    # The port can be configured as needed.
    # Debug mode should be False in a production environment.
    app.run(host='0.0.0.0', port=5001, debug=True)
