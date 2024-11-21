import uuid, math, json, asyncio,logging
from datetime import datetime
from fastembed import TextEmbedding
from openai import AsyncOpenAI
from qdrant_client import models, AsyncQdrantClient
from typing import Union


class Memory:
    prompt_memory_retention = """
You are an AI assistant specialized in analyzing human memory patterns. Your task is to evaluate information or events provided by users and assign an appropriate memory strength parameter (S value) based on the Ebbinghaus Forgetting Curve model.

S value range explanation:
1. High S value (1000-2000): Events that have a significant impact on life or evoke strong emotional responses. Examples: weddings, childbirth, major achievements.
2. Medium S value (100-500): Events of some importance but not critical to one's life. Examples: vacations, learning new skills, social activities.
3. Low S value (1-10): Ordinary events in daily life that usually don't attract special attention. Examples: daily meals, routine tasks.

Based on the information provided by the user, assess its importance, emotional intensity, and impact on life, then provide an appropriate S value (can be a decimal). Also, briefly explain your reasoning for the given S value.

User input: [User's information or event]

Your response should be a json object include:
1. Estimated S value
2. S value range (Low/Medium/High)
3. Brief explanation for the given S value

output format example:
{
    "S_value": 1.0,
    "S_value_range": "Low",
    "explanation": "The memory is about a daily routine, so the S value is low"
}
    """

    def __init__(
        self,
        qdrant_url: str = "http://192.168.5.179:6333",
        embedding_model: str = "snowflake/snowflake-arctic-embed-s",
        oai_api_key: str = "sk-d8db153b782a44b1a25d1bb6784ae42e",
        oai_base_url: str = "https://api.deepseek.com/v1",
        oai_model: str = "deepseek-chat",
        collection_name: str = "memory_collection",
    ):
        self.client = AsyncQdrantClient(url=qdrant_url)
        self.embedding_model = TextEmbedding(
            embedding_model, cache_dir="./memory/embeddings_cache"
        )
        self.collection_name = collection_name
        self.OAI_async_client = AsyncOpenAI(
            base_url=oai_base_url,
            api_key=oai_api_key,
        )
        self.oai_model = oai_model

    async def init_collection(self):
        await self.upsert_collection()
    
    async def close_client(self):
        await self.client.close()

    # Memory Operations Functions
    async def get_embedding(self, text: str):
        documents = [text]
        embeddings = list(self.embedding_model.embed(documents))[0]
        return embeddings.tolist()

    async def calculate_memory_retention(
        self, S_value_of_retention: float, memory_date: str
    ):
        days_between = (
            datetime.now() - datetime.strptime(memory_date, "%Y-%m-%d")
        ).days
        return round(math.exp(-days_between / S_value_of_retention), 4)

    async def upsert_collection(
        self,
        collection_name: str = None,
        vectors: dict[str, tuple[int, models.Distance]] = None,
    ):
        if collection_name is None:
            collection_name = self.collection_name
        if not await self.client.collection_exists(collection_name=collection_name):
            payload_config = {
                "collection_name": collection_name,
            }

            if vectors is not None:
                payload_config["vectors_config"] = {
                    vector_name: models.VectorParams(
                        size=vector_size,
                        distance=distance,
                    )
                    for vector_name, (vector_size, distance) in vectors.items()
                }
            else:
                payload_config["vectors_config"] = models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE,
                )

            payload_config["hnsw_config"] = models.HnswConfigDiff(
                m=16,
                ef_construct=100,
            )
            try:
                await self.client.create_collection(**payload_config)
                print(f"Collection {collection_name} created successfully")
                self.collection_name = collection_name
                return True
            except Exception as e:
                print(f"Error creating collection: {e}")
                return False
        else:
            print(f"Collection {collection_name} already exists")
            self.collection_name = collection_name
            collection_info = await self.client.get_collection(
                collection_name=collection_name
            )
            # print(f"Collection {collection_name} info: {collection_info}")
            return collection_info

    async def evaluate_memory_retention(self, description: str):
        messages = [
            {"role": "system", "content": self.prompt_memory_retention},
            {"role": "user", "content": description},
        ]
        response = await self.send_message(messages, json_output=True)
        return response.content

    async def add_memory(
        self,
        collection_name: str = None,
        vector_name: str = None,
        description: str = None,
        S_value_of_retention: float = 1,
        memory_level: str = "user-level",
        memory_type: str = "short-term",
        memory_category: str = "life events",
        memory_date: str = None,
        owner: str = "assistant",
        user_name: str = "user",
        char_uid: str = "char_uid",
        user_uid: str = "user_uid",
        is_previous_summary: bool = False,
    ):
        if collection_name is None:
            collection_name = self.collection_name
        if memory_date is None:
            memory_date = datetime.now().strftime("%Y-%m-%d")
        id_of_memory = str(uuid.uuid4())
        if is_previous_summary:
            namespace = uuid.NAMESPACE_DNS
            id_of_memory = str(
                uuid.uuid5(namespace, f"previous-summary-for-{char_uid}-{user_uid}")
            )
            memory_level = "system-level"
            memory_type = "persistent"
            memory_category = "previous-summary"
            S_value_of_retention = 100000

        payload = {
            "char_uid": char_uid,
            "user_uid": user_uid,
            "owner": owner,
            "user_name": user_name,
            "memory_level": memory_level,
            "memory_type": memory_type,
            "memory_category": memory_category,
            "memory_content": {
                "description": description,
            },
            "memory_date": memory_date,
            "S_value_of_retention": S_value_of_retention,
            "memory_retention": 1.0,
        }
        try:
            vector_embeded = await self.get_embedding(description)
            point_struct = {
                "id": id_of_memory,
                "payload": payload,
                "vector": (
                    {vector_name: vector_embeded}
                    if vector_name is not None
                    else vector_embeded
                ),
            }
            await self.client.upsert(
                collection_name=collection_name,
                points=[models.PointStruct(**point_struct)],
            )
            return f"Memory added for {owner} successfully, the description is: {description}, the id of the memory is: {id_of_memory}"
        except Exception as e:
            print(e)

    async def search_memory(
        self,
        dialog: list,
        convert_dialog_to_query: bool = False,
        is_previous_summary: bool = False,
        char_uid: str = None,
        user_uid: str = None,
        owner: str = None,
        user_name: str = None,
        memory_level: str = None,
        memory_type: str = None,
        collection_name: str = None,
        filter_method: str = "must",
        vector_name: str = None,
        limit: int = 5,
        with_payload: Union[bool, list[str]] = [
            "memory_content.description",
            "memory_date",
        ],
        with_vectors: bool = True,
    ):
        dialog_str = ""
        for message in dialog:
            if message["role"] == "user":
                dialog_str += f"{user_name}: {message['content']}\n"
            elif message["role"] == "assistant":
                dialog_str += f"{owner}: {message['content']}\n"
        if convert_dialog_to_query:
            # create a system prompt to tell the model to summarize the dialog into a query for a search in vector database from user's perspective
            system_prompt = f"""
You are an AI expert with advanced memory management capabilities. 
Your task is to analyze conversation between {owner} and {user_name}, and summarize the dialog into a 'Query' for a search in vector database about {user_name}'s questions or requests, 
Note, in {user_name}'s dialog, "I" means {user_name}, "you" means {owner}, "we" means {owner} and {user_name} or any other people in the conversation,
for example:
"{user_name}: What is my skill?" -> "What is {user_name}'s skill?",
"{user_name}: how about your mom?" -> "how about {owner}'s mom?",
"{user_name}: what does Mary go to do?" -> "what does Mary go to do?",
"{user_name}: what did you do last night?" -> "what did {owner} do last night?",
"{user_name}: what did we do last week?" -> "what did {owner} and {user_name} do last week?",
output the query result only, no other words or explanation.
        """
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": dialog_str},
            ]
            message = await self.send_message(messages=messages, json_output=False)
            await asyncio.sleep(0.5)
            query = message.content
            logging.info(f"The query is: {query}")
        else:
            query = dialog_str
        # print(f"The query is: {query}")
        if collection_name is None:
            collection_name = self.collection_name
        filter_list = []
        if char_uid is not None:
            filter_list.append(
                models.FieldCondition(
                    key="char_uid", match=models.MatchValue(value=char_uid)
                )
            )
        if owner is not None:
            filter_list.append(
                models.FieldCondition(key="owner", match=models.MatchValue(value=owner))
            )
        if user_uid is not None:
            filter_list.append(
                models.FieldCondition(
                    key="user_uid", match=models.MatchValue(value=user_uid)
                )
            )
        if user_name is not None:
            filter_list.append(
                models.FieldCondition(
                    key="user_name", match=models.MatchValue(value=user_name)
                )
            )
        if memory_level is not None:
            filter_list.append(
                models.FieldCondition(
                    key="memory_level", match=models.MatchValue(value=memory_level)
                )
            )
        if memory_type is not None:
            filter_list.append(
                models.FieldCondition(
                    key="memory_type", match=models.MatchValue(value=memory_type)
                )
            )
        filter_condition = {filter_method: filter_list}
        search_query_payload = {
            "collection_name": collection_name,
            "query": await self.get_embedding(query),
            "query_filter": models.Filter(**filter_condition),
            "limit": limit,
            "with_payload": with_payload,
            "with_vectors": with_vectors,
        }
        if vector_name is not None:
            search_query_payload["using"] = vector_name

        search_result = await self.client.query_points(**search_query_payload)
        if len(search_result.points) == 0:
            return None
        else:
            # search_result.points.sort(key=lambda x: x.score, reverse=True)
            if is_previous_summary:
                return search_result.points[0].payload.get("memory_content", {}).get(
                    "description", "unknown"
                )
            else:
                results = []
                for index, point in enumerate(search_result.points):
                    memory_date = point.payload.get("memory_date", "unknown")
                    description = point.payload.get("memory_content", {}).get(
                        "description", "unknown"
                    )
                    results.append(
                        f'Reference-[{index+1}] in {owner}\'s memory: "{description}" - created date: {memory_date} - point score: {point.score}'
                    )
                return "\n".join(results)

    async def delete_memory(
        self,
        filter_query_items: dict = {
            "owner": "assistant",
            "char_uid": "char_uid",
            "user_name": "user",
            "user_uid": "user_uid",
            "memory_level": "user-level",
        },
        filter_query_method: str = "must",
        collection_name: str = None,
    ):
        if collection_name is None:
            collection_name = self.collection_name
        field_condition = {filter_query_method: []}
        for key, value in filter_query_items.items():
            field_condition[filter_query_method].append(
                models.FieldCondition(key=key, match=models.MatchValue(value=value))
            )
        try:
            result = await self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(**field_condition)
                ),
            )
            return f"the operation result is: {result}"
        except Exception as e:
            print(e)
            return f"Error deleting memory for {filter_query_items}"

    async def update_memory_retention(
        self,
        collection_name: str = None,
        char_uid: str = None,
        owner: str = None,
        user_uid: str = None,
        user_name: str = None,
        memory_level: str = None,
    ):
        if collection_name is None:
            collection_name = self.collection_name
        filter_list = []
        if char_uid is not None:
            filter_list.append(
                models.FieldCondition(
                    key="char_uid", match=models.MatchValue(value=char_uid)
                )
            )
        if owner is not None:
            filter_list.append(
                models.FieldCondition(key="owner", match=models.MatchValue(value=owner))
            )
        if user_uid is not None:
            filter_list.append(
                models.FieldCondition(
                    key="user_uid", match=models.MatchValue(value=user_uid)
                )
            )
        if user_name is not None:
            filter_list.append(
                models.FieldCondition(
                    key="user_name", match=models.MatchValue(value=user_name)
                )
            )
        if memory_level is not None:
            filter_list.append(
                models.FieldCondition(
                    key="memory_level", match=models.MatchValue(value=memory_level)
                )
            )
        setup_dict = {
            "collection_name": collection_name,
            "limit": 1,
            "with_payload": True,
            "with_vectors": False,
            "scroll_filter": models.Filter(must=filter_list),
        }
        offset_id = None
        while True:
            result = await self.client.scroll(**setup_dict, offset=offset_id)
            if len(result[0]) == 0:
                return "there is no memory to update"
            for point in result[0]:
                S_value_of_retention = point.payload["S_value_of_retention"]
                memory_date = point.payload["memory_date"]
                memory_retention = await self.calculate_memory_retention(
                    S_value_of_retention, memory_date
                )
                await self.client.set_payload(
                    collection_name=collection_name,
                    points=[point.id],
                    payload={"memory_retention": memory_retention},
                )
            if result[1] is not None:
                offset_id = result[1]
            else:
                return "Memory retention updated successfully"

    # Chat Operations Functions
    async def send_message(
        self,
        messages: list,
        tools: list = None,
        temperature: float = 0.7,
        json_output: bool = False,
    ):
        payload = {
            "model": self.oai_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        await asyncio.sleep(0.2)
        response = await self.OAI_async_client.chat.completions.create(**payload)
        return response.choices[0].message

    async def judge_dialog_if_need_search_memory(
        self, dialog: list, owner: str, user_name: str
    ):
        dialog_str = ""
        for message in dialog:
            if message["role"] == "user":
                dialog_str += f"{user_name}: {message['content']}\n"
            elif message["role"] == "assistant":
                dialog_str += f"{owner}: {message['content']}\n"
        system_prompt = f"""
You are an AI assistant. Your task is to judge if the given dialog between {owner} and {user_name} needs to search memory.
The criteria for needing to search memory are:
1. the question is about someone's information ({user_name}, {owner}, or other people), such as hobbies, interests, or life events, etc.
2. the question is about {user_name} asked {owner} to do something (join for a drink, go to a movie, have sex, etc.) that critically depends on {owner}'s hobbies, interests, favorite things, personality, sexual preferences, etc.
3. the question is about relationship information related to {owner} or {user_name}, such as relationship status, romantic status, work relationship, etc.
4. the question is about something that highly related to the topic in the dialog details, it depends on your judgement.
5. the question is about specific information have not mentioned in the dialog details, {owner} need to refer to the memory to answer the question.

output your judgement in json object format:
{{
    "if_need_search_memory": true or false,
    "reason": "your explanation of your judgment"
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": dialog_str},
        ]
        message = await self.send_message(messages=messages, json_output=True)
        await asyncio.sleep(0.5)
        return message.content

    async def judge_dialog_if_need_add_memory(
        self,
        dialog: list,
        owner: str,
        user_name: str,
    ):
        messages = [
            {
                "role": "system",
                "content": f"""You are an AI expert with advanced memory management capabilities. Your task is to analyze conversation, the conversation can be both part of role-play or real life, determining is there any information worth remembering and add them to memory system.
In the given conversation, there are two persons: {owner} and {user_name}.
Criteria for worth-remembering information:
1. Important events or stories that {owner} or {user_name} have, or have experienced, such as birthdays, holidays, or significant life changes, etc.
2. Significant facts about {owner} or {user_name}, such as major achievements, awards, or recognitions, etc.
3. Involved role-play or real life details such as name, favorites, interests, habits, hobbies, hates, fears, marriage status, love status, etc.
4. Relationship information related to {owner} or {user_name}.
5. Sexual information about {owner} or {user_name}, such as favorite sex position, favorite sexual activity, sexual preferences, sexual fantasies, sexual skills, etc.

For memory information in conversation, you should:
1. Judge if the memory is worthy to add to memory database according to the criteria.
2. Describe the detail information of the memory with complete sentences from {owner}'s perspective, using past tense to emphasize that these are past events or information.
3. Categorize the memory as either 'short-term' or 'long-term' memory base on the content of the memory.
4. Assign a category to the memory: 'persona', 'life events', 'relationship', or 'other'.
5. combine all the results of your judgement in just One json object to output, no other words or explanation:
{{
    "is_worthy_to_add_to_memory_database": true or false, boolean value, according to the criteria
    "description": "The description of all the memory information in the dialog, using past tense to emphasize that these are past events or information",
    "memory_type": "short-term" or "long-term",
    "memory_category": "persona", "life events", "relationship", or "other",
    "reason": "The reason why you decide to add or not add this memory according to the criteria"
}}
""",
            },
        ]
        conversation_history = ""
        for message in dialog:
            if message["role"] == "user":
                conversation_history += f"{user_name}: {message['content']}\n"
            else:
                conversation_history += f"{owner}: {message['content']}\n"

        messages.append({"role": "user", "content": conversation_history})
        message = await self.send_message(
            messages=messages,
            json_output=True,
        )
        await asyncio.sleep(0.5)
        return message.content

    async def judge_if_memory_has_exsited(
        self,
        char_uid: str = None,
        user_uid: str = None,
        collection_name: str = None,
        vector_name: str = None,
        owner: str = None,
        user_name: str = None,
        dialog: list = None,
    ):
        if collection_name is None:
            collection_name = self.collection_name
        setup_dict = {
            "collection_name": collection_name,
        }
        if vector_name is not None:
            setup_dict["vector_name"] = vector_name
        result = await self.search_memory(
            dialog=dialog,
            char_uid=char_uid,
            user_uid=user_uid,
            owner=owner,
            user_name=user_name,
            memory_level="user-level",
            **setup_dict,
        )
        if result is None:
            return json.dumps(
                {"has_existed": False, "reason": "no memory reference found"}
            )
        else:
            dialog_str = ""
            for message in dialog:
                if message["role"] == "user":
                    dialog_str += f"{user_name}: {message['content']}\n"
                elif message["role"] == "assistant":
                    dialog_str += f"{owner}: {message['content']}\n"
            messages = [
                {
                    "role": "system",
                    "content": f'You are a memory assistant. Your task is to judge: Case A: if the topic or event details in the user-given dialog already exist in the memory reference, or Case B: if there are any new topics or event details in the dialog that do not exist in the memory reference.\n If the result is Case A, output a JSON object: \'{{"has_existed":true, "reason":"your explanation of your judgment"}}\'. If the result is Case B, output \'{{"has_existed":false, "reason":"your explanation of your judgment"}}\'. Do not output any other words.',
                },
                {
                    "role": "user",
                    "content": f"The memory reference of {owner} is: \n{result}\n The dialog is: \n{dialog_str}",
                },
            ]
            # print(messages)
            message = await self.send_message(messages=messages, json_output=True)
            await asyncio.sleep(0.5)
            return message.content

    async def memory_previous_summary(
        self, owner: str, user_name: str, plot_description: str, dialog: list
    ):
        system_prompt = f"""
You are an AI expert with advanced memory management capabilities. 
Your task is to generate a previous summary in 2 perspectives:
previous_summary_narrator: like a narrator telling what happened according to the plot description and dialog between {owner} and {user_name}.
previous_summary_owner: like {owner} telling {user_name} what happened in first person perspective that according to the plot description and dialog between {owner} and {user_name}, the structure of the summary should be like as below:
"I remember [the concise description of what happened in past], and now [the detail of latest situation]", note: use "I" for {owner}, use "you" for {user_name}

output your summary result only in json object format:
{{
    "previous_summary_narrator": "The previous summary of the plot according to the plot description and dialog between {owner} and {user_name}",
    "previous_summary_owner": "The previous summary of the plot according to the plot description and dialog between {owner} and {user_name} in first person perspective",
    "the_latest_words_1": "The latest input from {user_name} in the dialog, for example: 'the input from {user_name}'",
    "the_latest_words_2": "The latest output from {owner} in the dialog, for example: 'the output from {owner}'",
}}
"""
        previous_dialog = "\n".join(dialog)
        user_prompt = f"The plot description is: \n{plot_description}\n The dialog is: \n{previous_dialog}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        message = await self.send_message(messages=messages, json_output=True)
        await asyncio.sleep(0.5)
        return message.content

    async def fetch_previous_summary(
        self, char_uid: str, user_uid: str, owner: str, user_name: str, vector_name: str
    ):
        dialog = [
            {
                "role": "user",
                "content": "Search for previous summary of the plot",
            }
        ]
        result = await self.search_memory(
            dialog=dialog,
            char_uid=char_uid,
            user_uid=user_uid,
            owner=owner,
            user_name=user_name,
            memory_level="system-level",
            vector_name=vector_name,
            limit=1,
            is_previous_summary=True,
        )
        if result is None:
            return None
        else:
            return json.loads(result)
