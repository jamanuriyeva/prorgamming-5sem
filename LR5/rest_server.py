from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import grpc
from concurrent import futures

# Импортируем наши gRPC модули
import glossary_pb2
import glossary_pb2_grpc
import json
import os

app = Flask(__name__)
CORS(app)


class GlossaryService(glossary_pb2_grpc.GlossaryServiceServicer):
    def __init__(self):
        self.data_file = 'glossary_data.json'
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.glossary = json.load(f)
        else:
            self.glossary = {
                "list": {
                    "term": "list",
                    "definition": "Встроенный тип данных в Python, представляющий упорядоченную изменяемую коллекцию элементов",
                    "category": "Data Structures",
                    "examples": ["my_list = [1, 2, 3]", "my_list.append(4)"],
                    "created_at": "2024-01-01 10:00:00",
                    "updated_at": "2024-01-01 10:00:00"
                },
                "dictionary": {
                    "term": "dictionary",
                    "definition": "Встроенный тип данных в Python, представляющий неупорядоченную коллекцию пар ключ-значение",
                    "category": "Data Structures",
                    "examples": ["my_dict = {'key': 'value'}", "value = my_dict['key']"],
                    "created_at": "2024-01-01 10:00:00",
                    "updated_at": "2024-01-01 10:00:00"
                }
            }
            self.save_data()

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.glossary, f, ensure_ascii=False, indent=2)

    def GetTerm(self, request, context):
        term_key = request.term.lower()
        if term_key in self.glossary:
            term_data = self.glossary[term_key]
            return glossary_pb2.TermResponse(
                term=term_data['term'],
                definition=term_data['definition'],
                category=term_data['category'],
                examples=term_data['examples'],
                created_at=term_data['created_at'],
                updated_at=term_data['updated_at']
            )
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Term '{request.term}' not found")
            return glossary_pb2.TermResponse()

    def SearchTerms(self, request, context):
        query = request.query.lower()
        results = []

        for term_key, term_data in self.glossary.items():
            if (query in term_key or
                    query in term_data['definition'].lower() or
                    query in term_data['category'].lower()):
                results.append(glossary_pb2.TermResponse(
                    term=term_data['term'],
                    definition=term_data['definition'],
                    category=term_data['category'],
                    examples=term_data['examples'],
                    created_at=term_data['created_at'],
                    updated_at=term_data['updated_at']
                ))

        return glossary_pb2.SearchTermsResponse(
            terms=results,
            total_count=len(results)
        )

    def AddTerm(self, request, context):
        term_key = request.term.lower()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        if term_key in self.glossary:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"Term '{request.term}' already exists")
            return glossary_pb2.OperationResponse(success=False, message="Term already exists")

        self.glossary[term_key] = {
            "term": request.term,
            "definition": request.definition,
            "category": request.category,
            "examples": list(request.examples),
            "created_at": current_time,
            "updated_at": current_time
        }

        self.save_data()
        return glossary_pb2.OperationResponse(
            success=True,
            message=f"Term '{request.term}' added successfully"
        )

    def ListAllTerms(self, request, context):
        all_terms = list(self.glossary.values())

        term_responses = []
        for term_data in all_terms:
            term_responses.append(glossary_pb2.TermResponse(
                term=term_data['term'],
                definition=term_data['definition'],
                category=term_data['category'],
                examples=term_data['examples'],
                created_at=term_data['created_at'],
                updated_at=term_data['updated_at']
            ))

        return glossary_pb2.ListAllResponse(
            terms=term_responses,
            total_count=len(all_terms),
            page=1,
            page_size=len(all_terms)
        )


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    glossary_pb2_grpc.add_GlossaryServiceServicer_to_server(GlossaryService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC Server started on port 50051")
    server.wait_for_termination()


# Запускаем gRPC сервер в фоне
print("Starting gRPC server...")
grpc_thread = threading.Thread(target=serve_grpc)
grpc_thread.daemon = True
grpc_thread.start()

# Ждем немного чтобы gRPC сервер запустился
time.sleep(2)


# Создаем клиент для REST API
class GlossaryClient:
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = glossary_pb2_grpc.GlossaryServiceStub(self.channel)

    def get_term(self, term):
        try:
            response = self.stub.GetTerm(glossary_pb2.GetTermRequest(term=term))
            return response
        except grpc.RpcError as e:
            return None

    def search_terms(self, query):
        try:
            response = self.stub.SearchTerms(glossary_pb2.SearchTermsRequest(query=query))
            return response
        except grpc.RpcError as e:
            return None

    def add_term(self, term, definition, category, examples=None):
        try:
            if examples is None:
                examples = []
            response = self.stub.AddTerm(glossary_pb2.AddTermRequest(
                term=term,
                definition=definition,
                category=category,
                examples=examples
            ))
            return response
        except grpc.RpcError as e:
            return None

    def list_all_terms(self):
        try:
            response = self.stub.ListAllTerms(glossary_pb2.ListAllRequest())
            return response
        except grpc.RpcError as e:
            return None


glossary_client = GlossaryClient()


# REST API endpoints
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Python Glossary</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
            input, textarea { width: 100%; padding: 8px; margin: 5px 0; }
            button { background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            .term { background: #f5f5f5; padding: 15px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Python Glossary</h1>

            <div class="card">
                <h3>Add New Term</h3>
                <input type="text" id="term" placeholder="Term (e.g., list)" />
                <input type="text" id="category" placeholder="Category (e.g., Data Structures)" />
                <textarea id="definition" placeholder="Definition" rows="3"></textarea>
                <textarea id="examples" placeholder="Examples (one per line)" rows="3"></textarea>
                <button onclick="addTerm()">Add Term</button>
            </div>

            <div class="card">
                <h3>Search Terms</h3>
                <input type="text" id="search" placeholder="Search..." onkeyup="searchTerms()" />
                <div id="searchResults"></div>
            </div>

            <div class="card">
                <h3>All Terms</h3>
                <button onclick="loadAllTerms()">Load All Terms</button>
                <div id="allTerms"></div>
            </div>
        </div>

        <script>
            async function addTerm() {
                const term = document.getElementById('term').value;
                const category = document.getElementById('category').value;
                const definition = document.getElementById('definition').value;
                const examples = document.getElementById('examples').value.split('\\n').filter(e => e.trim());

                const response = await fetch('/api/terms', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ term, category, definition, examples })
                });

                const result = await response.json();
                alert(result.message);
                if (result.success) {
                    document.getElementById('term').value = '';
                    document.getElementById('category').value = '';
                    document.getElementById('definition').value = '';
                    document.getElementById('examples').value = '';
                    loadAllTerms();
                }
            }

            async function searchTerms() {
                const query = document.getElementById('search').value;
                if (query.length < 2) {
                    document.getElementById('searchResults').innerHTML = '';
                    return;
                }

                const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                const terms = await response.json();

                let html = '<h4>Search Results:</h4>';
                terms.forEach(term => {
                    html += `
                        <div class="term">
                            <strong>${term.term}</strong> (${term.category})<br>
                            ${term.definition}<br>
                            <em>Examples: ${term.examples?.join(', ') || 'None'}</em>
                        </div>
                    `;
                });

                document.getElementById('searchResults').innerHTML = html;
            }

            async function loadAllTerms() {
                const response = await fetch('/api/terms');
                const terms = await response.json();

                let html = '<h4>All Terms:</h4>';
                terms.forEach(term => {
                    html += `
                        <div class="term">
                            <strong>${term.term}</strong> (${term.category})<br>
                            ${term.definition}<br>
                            <em>Examples: ${term.examples?.join(', ') || 'None'}</em>
                        </div>
                    `;
                });

                document.getElementById('allTerms').innerHTML = html;
            }

            window.onload = loadAllTerms;
        </script>
    </body>
    </html>
    '''


@app.route('/api/terms', methods=['GET'])
def get_terms():
    try:
        term = request.args.get('term')
        if term:
            result = glossary_client.get_term(term)
            if result and hasattr(result, 'term') and result.term:
                return jsonify({
                    'term': result.term,
                    'definition': result.definition,
                    'category': result.category,
                    'examples': list(result.examples)
                })
            else:
                return jsonify({'error': 'Term not found'}), 404
        else:
            result = glossary_client.list_all_terms()
            if result:
                terms = []
                for term in result.terms:
                    terms.append({
                        'term': term.term,
                        'definition': term.definition,
                        'category': term.category,
                        'examples': list(term.examples)
                    })
                return jsonify(terms)
            return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/terms', methods=['POST'])
def add_term():
    try:
        data = request.json
        result = glossary_client.add_term(
            data['term'],
            data['definition'],
            data['category'],
            data.get('examples', [])
        )
        if result:
            return jsonify({'success': result.success, 'message': result.message})
        return jsonify({'error': 'Failed to add term'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search_terms():
    try:
        query = request.args.get('q', '')
        result = glossary_client.search_terms(query)
        if result:
            terms = []
            for term in result.terms:
                terms.append({
                    'term': term.term,
                    'definition': term.definition,
                    'category': term.category,
                    'examples': list(term.examples)
                })
            return jsonify(terms)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'Python Glossary API'})


if __name__ == '__main__':
    print("Starting REST API server on http://localhost:5000")
    print("Open your browser and go to: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)