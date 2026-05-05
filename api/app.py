import os
import sys

# Allow running from flask/ or from spec-doc/flask/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from create_app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3101))
    print(f'[Flask] Starting on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
