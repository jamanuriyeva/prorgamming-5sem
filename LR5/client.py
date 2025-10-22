import grpc
import glossary_pb2
import glossary_pb2_grpc


class GlossaryClient:
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = glossary_pb2_grpc.GlossaryServiceStub(self.channel)

    def get_term(self, term):
        try:
            response = self.stub.GetTerm(glossary_pb2.GetTermRequest(term=term))
            return response
        except grpc.RpcError as e:
            return f"Error: {e.details()}"

    def search_terms(self, query):
        try:
            response = self.stub.SearchTerms(glossary_pb2.SearchTermsRequest(query=query))
            return response
        except grpc.RpcError as e:
            return f"Error: {e.details()}"

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
            return f"Error: {e.details()}"

    def update_term(self, term, definition, category, examples=None):
        try:
            if examples is None:
                examples = []
            response = self.stub.UpdateTerm(glossary_pb2.UpdateTermRequest(
                term=term,
                definition=definition,
                category=category,
                examples=examples
            ))
            return response
        except grpc.RpcError as e:
            return f"Error: {e.details()}"

    def delete_term(self, term):
        try:
            response = self.stub.DeleteTerm(glossary_pb2.DeleteTermRequest(term=term))
            return response
        except grpc.RpcError as e:
            return f"Error: {e.details()}"

    def list_all_terms(self, page=1, page_size=10):
        try:
            response = self.stub.ListAllTerms(glossary_pb2.ListAllRequest(
                page=page, page_size=page_size
            ))
            return response
        except grpc.RpcError as e:
            return f"Error: {e.details()}"


def main():
    client = GlossaryClient()

    while True:
        print("\n=== Python Glossary gRPC Client ===")
        print("1. Get term")
        print("2. Search terms")
        print("3. Add term")
        print("4. Update term")
        print("5. Delete term")
        print("6. List all terms")
        print("7. Exit")

        choice = input("Choose option: ")

        if choice == '1':
            term = input("Enter term: ")
            result = client.get_term(term)
            if hasattr(result, 'term'):
                print(f"\nTerm: {result.term}")
                print(f"Definition: {result.definition}")
                print(f"Category: {result.category}")
                print(f"Examples: {result.examples}")
            else:
                print(result)

        elif choice == '2':
            query = input("Enter search query: ")
            result = client.search_terms(query)
            if hasattr(result, 'terms'):
                print(f"\nFound {result.total_count} terms:")
                for term in result.terms:
                    print(f"- {term.term}: {term.definition[:50]}...")
            else:
                print(result)

        elif choice == '3':
            term = input("Enter term: ")
            definition = input("Enter definition: ")
            category = input("Enter category: ")
            examples = input("Enter examples (comma-separated): ").split(',')
            examples = [ex.strip() for ex in examples if ex.strip()]

            result = client.add_term(term, definition, category, examples)
            print(f"Result: {result.message}")

        elif choice == '4':
            term = input("Enter term to update: ")
            definition = input("Enter new definition: ")
            category = input("Enter new category: ")
            examples = input("Enter new examples (comma-separated): ").split(',')
            examples = [ex.strip() for ex in examples if ex.strip()]

            result = client.update_term(term, definition, category, examples)
            print(f"Result: {result.message}")

        elif choice == '5':
            term = input("Enter term to delete: ")
            result = client.delete_term(term)
            print(f"Result: {result.message}")

        elif choice == '6':
            page = int(input("Enter page (default 1): ") or 1)
            page_size = int(input("Enter page size (default 10): ") or 10)

            result = client.list_all_terms(page, page_size)
            if hasattr(result, 'terms'):
                print(f"\nPage {result.page} of {result.total_count} terms:")
                for term in result.terms:
                    print(f"\n- {term.term}")
                    print(f"  Definition: {term.definition}")
                    print(f"  Category: {term.category}")
            else:
                print(result)

        elif choice == '7':
            break


if __name__ == '__main__':
    main()