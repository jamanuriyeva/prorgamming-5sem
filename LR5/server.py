import grpc
from concurrent import futures
import time
import json
import os
from datetime import datetime

import glossary_pb2
import glossary_pb2_grpc


class GlossaryService(glossary_pb2_grpc.GlossaryServiceServicer):
    def __init__(self):
        self.data_file = 'glossary_data.json'
        self.load_data()

    def load_data(self):
        """Загружаем данные из JSON файла"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.glossary = json.load(f)
        else:
            # Инициализируем базовыми терминами Python
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
                },
                "function": {
                    "term": "function",
                    "definition": "Блок кода, который выполняется только при его вызове",
                    "category": "Functions",
                    "examples": ["def my_function():", "result = my_function()"],
                    "created_at": "2024-01-01 10:00:00",
                    "updated_at": "2024-01-01 10:00:00"
                }
            }
            self.save_data()

    def save_data(self):
        """Сохраняем данные в JSON файл"""
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
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    def UpdateTerm(self, request, context):
        term_key = request.term.lower()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if term_key not in self.glossary:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Term '{request.term}' not found")
            return glossary_pb2.OperationResponse(success=False, message="Term not found")

        self.glossary[term_key].update({
            "definition": request.definition,
            "category": request.category,
            "examples": list(request.examples),
            "updated_at": current_time
        })

        self.save_data()
        return glossary_pb2.OperationResponse(
            success=True,
            message=f"Term '{request.term}' updated successfully"
        )

    def DeleteTerm(self, request, context):
        term_key = request.term.lower()

        if term_key not in self.glossary:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Term '{request.term}' not found")
            return glossary_pb2.OperationResponse(success=False, message="Term not found")

        del self.glossary[term_key]
        self.save_data()
        return glossary_pb2.OperationResponse(
            success=True,
            message=f"Term '{request.term}' deleted successfully"
        )

    def ListAllTerms(self, request, context):
        page = request.page or 1
        page_size = request.page_size or 10

        all_terms = list(self.glossary.values())
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        paginated_terms = all_terms[start_idx:end_idx]

        term_responses = []
        for term_data in paginated_terms:
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
            page=page,
            page_size=page_size
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    glossary_pb2_grpc.add_GlossaryServiceServicer_to_server(GlossaryService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC Server started on port 50051")

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()