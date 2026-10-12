from time import sleep
import logging
import requests
from ..models.query import BiotoolsHit

logger = logging.getLogger(__name__)

class BiotoolsSearcher:
    def __init__(self):
        self.filter_keys = { "topic": "topicID", "operation": "operationID", "data": "dataTypeID", "format": "dataFormatID" }
    
    def _explore_api_url(self, matches, url, tool_ids=[]):
        r = requests.get(url, timeout=(3.05, 30) )
        r.raise_for_status()
        data = r.json()
        next_page = data['next']

        for d in data['list']:
            _id = d['biotoolsID']
            if( _id not in tool_ids ):
                tool_ids.add(_id)

                name = d['name']
                description = d['description']
                biotools_link = f"https://bio.tools/{_id}"

                topic_list = list( map( lambda x: x['uri'], d['topic'] ))
                
                data_list = []
                format_list = []
                operation_list = [] 
                function_elements = d['function']
                for fel in function_elements:
                    if( "operation" in fel ):
                        operation_list += list( map( lambda x: x['uri'], fel['operation'] ))
                    
                    if( "input" in fel ):
                        inputs = fel['input']
                        for el in inputs:
                            data_list += [ el['data']['uri'] ]
                            format_list += list( map( lambda x: x['uri'], el['format'] ))
                    
                    if( "output" in fel ):
                        outputs = fel['output']
                        for el in outputs:
                            data_list += [ el['data']['uri'] ]
                            format_list += list( map( lambda x: x['uri'], el['format'] ))
                
                if( (len(topic_list) > 0) or (len(operation_list) > 0) or (len(data_list) > 0) or (len(format_list) > 0) ):
                    h = BiotoolsHit(
                        name = name,
                        description = description,
                        biotools_link = biotools_link,
                        topic_terms = list(set(topic_list)),
                        operation_terms = list(set(operation_list)),
                        data_terms = list(set(data_list)),
                        format_terms = list(set(format_list)),
                    )
                matches.append(h)
                sleep(1)

        return next_page, matches, tool_ids

    def query_by_text(
        self, 
        seed: str,
        max_results: int = 10,
    ) -> list[BiotoolsHit]:
        """Search for a tool in Biotools database using a keyword as seed that is a textual description

        Args:
            seed: Textual keyword to search in tool names and descriptions.
            max_results: Maximum number of matches to return.

        Returns:
            List of Biotools tools that matched the keyword
        """

        tool_ids = set()

        matches = []
        url = f"https://bio.tools/api/t/?q=%22{seed}%22&format=json&per_page=100"
        r = requests.get(url, timeout=(3.05, 30) )
        r.raise_for_status()
        data = r.json()
        total = data['count']
        next_page = data['next']
        next_page, matches, tool_ids = self._explore_api_url( matches, url, tool_ids)

        while( (len(matches) < max_results) and (next_page is not None) ):
            url_search = f"{url}{next_page}"
            next_page, matches, tool_ids = self._explore_api_url( matches, url_search, tool_ids)

        logger.info(f"There are {total} tools in bio.tools related to your keyword, displaying only {max_results}")

        return matches[:max_results]

    def _solve_edam_category_url(self, uri):
        term = uri.split("/")[-1]
        category = term.split("_")[0]
        filter_parameter = self.filter_keys[category]
        url_search = f"https://bio.tools/api/t/?{filter_parameter}={term}&format=json&per_page=100"
        
        return url_search

    def query_by_edam_terms(
        self, 
        edam_terms: list[str],
        max_results: int = 10,
    ) -> list[BiotoolsHit]:
        """Search for a tool in Biotools database using a list of mapped EDAM URI terms

        Args:
            seed: A list of EDAM concept URIs to search in tool names and descriptions.
            max_results: Maximum number of matches to return.

        Returns:
            List of Biotools tools that matched the keyword
        """

        tool_ids = set()

        matches = []
        for uri in set(edam_terms):
            url = self._solve_edam_category_url(uri)

            r = requests.get(url, timeout=(3.05, 30) )
            r.raise_for_status()
            data = r.json()
            total = data['count']
            next_page = data['next']
            next_page, matches, tool_ids = self._explore_api_url( matches, url, tool_ids )

            while( (len(matches) < max_results) and (next_page is not None) ):
                url_search = f"{url}{next_page}"
                next_page, matches, tool_ids = self._explore_api_url( matches, url_search, tool_ids)

        logger.info(f"There are {total} tools in bio.tools related to your keyword, displaying only {max_results}")

        return matches[:max_results]
