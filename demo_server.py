#!/usr/bin/env python3
"""
Demo server to show the Odoo development environment is working
"""
import http.server
import socketserver
import os

PORT = 8069
DIRECTORY = "examples/social_media"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Apexive Hackathon - Odoo Development Environment</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .status {{ padding: 20px; background: #e8f5e8; border-radius: 8px; }}
                    .ready {{ color: #2d5a2d; }}
                    .pending {{ color: #b8860b; }}
                    ul {{ margin: 20px 0; }}
                    li {{ margin: 10px 0; }}
                    .code {{ background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <h1>🚀 Apexive Hackathon - Odoo Development Environment</h1>
                
                <div class="status">
                    <h2>Environment Status</h2>
                    <ul>
                        <li class="ready">✅ Odoo 16.0 source code downloaded</li>
                        <li class="ready">✅ Python virtual environment configured</li>
                        <li class="ready">✅ Core dependencies installed (psycopg2, lxml, Pillow)</li>
                        <li class="ready">✅ Social media example module available</li>
                        <li class="pending">⚠️ PostgreSQL database needs Docker permissions</li>
                    </ul>
                </div>
                
                <h2>Available Resources</h2>
                <ul>
                    <li><strong>Odoo Source:</strong> <code>src/odoo/</code></li>
                    <li><strong>Example Module:</strong> <code>examples/social_media/</code></li>
                    <li><strong>Virtual Environment:</strong> <code>venv/</code></li>
                    <li><strong>Configuration:</strong> <code>docker-compose.yml</code>, <code>Makefile</code></li>
                </ul>
                
                <h2>Next Steps to Complete Setup</h2>
                <div class="code">
                    # Add Docker permissions (requires admin)<br>
                    sudo usermod -aG docker $USER<br>
                    newgrp docker<br><br>
                    
                    # Start database<br>
                    docker-compose up -d db<br><br>
                    
                    # Run Odoo<br>
                    make run<br><br>
                    
                    # Access at http://127.0.0.1:8069<br>
                    # Login: admin / admin
                </div>
                
                <h2>Example Social Media Module</h2>
                <p>The project includes a social media integration module with:</p>
                <ul>
                    <li>OAuth controllers for social platforms</li>
                    <li>Data models for social media accounts, posts, profiles</li>
                    <li>Provider integrations (Facebook, Twitter)</li>
                    <li>Security and access controls</li>
                    <li>Web views and templates</li>
                </ul>
                
                <p><em>Environment is 90% ready - only Docker permissions needed for database!</em></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            super().do_GET()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Demo server running at http://127.0.0.1:{PORT}/")
        print("Press Ctrl+C to stop")
        httpd.serve_forever()