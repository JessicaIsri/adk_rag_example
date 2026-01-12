# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
RAG Orchestrator Agent - Routes between file management and search
"""

import logging
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGOrchestrator(BaseAgent):
    """
    Custom orchestrator for RAG workflow.

    Routes user requests to the appropriate agent:
    - File uploads/management → File Manager Agent
    - Search queries → Search Assistant Agent

    This agent checks session state and context to intelligently route requests.
    """

    # Declare sub-agents as class attributes for Pydantic
    file_manager: LlmAgent
    search_assistant: LlmAgent

    # Allow arbitrary types for Pydantic validation
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
            self,
            name: str,
            file_manager: LlmAgent,
            search_assistant: LlmAgent,
    ):
        """
        Initialize the RAG Orchestrator.

        Args:
            name: The name of the orchestrator
            file_manager: Agent that handles file uploads and indexing
            search_assistant: Agent that handles search and answers questions
        """
        # Define sub_agents list for framework
        sub_agents_list = [file_manager, search_assistant]

        # Call super().__init__ with all required fields
        super().__init__(
            name=name,
            file_manager=file_manager,
            search_assistant=search_assistant,
            sub_agents=sub_agents_list,
        )

    @override
    async def _run_async_impl(
            self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Orchestration logic for routing requests.
        """
        logger.info(f"[{self.name}] Starting RAG orchestration")

        # Check session state for routing hints
        state = ctx.session.state
        logger.info(f"[{self.name}] Session state: {state}")

        # Get the user's latest message from session history
        user_text = ""
        has_file_upload = False
        uploaded_filename = None

        # Check the latest user message from session events
        if ctx.session.events and len(ctx.session.events) > 0:
            # Get the most recent event
            last_event = ctx.session.events[-1]
            if last_event.content and last_event.content.parts:
                for idx, part in enumerate(last_event.content.parts):
                    if part.text:
                        user_text = part.text.lower()
                        logger.info(f"[{self.name}] User text: {user_text[:100]}")
                    # Check if this part contains a file (inline_data indicates upload)
                    if part.inline_data:
                        has_file_upload = True
                        mime_type = part.inline_data.mime_type
                        logger.info(f"[{self.name}] Detected file upload: {mime_type}")

                        # Generate a filename from MIME type if not provided
                        # Try to get filename from user text or generate one
                        if "file" in user_text or "/" in user_text:
                            # User might have typed filename
                            words = user_text.split()
                            for word in words:
                                if "." in word:
                                    uploaded_filename = word.strip()
                                    break

                        if not uploaded_filename:
                            # Generate filename from MIME type
                            ext = mime_type.split('/')[-1]
                            if ext == 'pdf':
                                uploaded_filename = f"uploaded_document_{idx}.pdf"
                            elif ext in ['png', 'jpg', 'jpeg']:
                                uploaded_filename = f"uploaded_image_{idx}.{ext}"
                            else:
                                uploaded_filename = f"uploaded_file_{idx}.{ext}"

                        # Note: File will be accessed directly from session history by tools
                        logger.info(f"[{self.name}] Upload will be processed as: {uploaded_filename}")

        # Routing Logic
        route_to_file_manager = False

        if has_file_upload:
            logger.info(f"[{self.name}] → Routing to File Manager (file upload detected)")
            route_to_file_manager = True

        elif any(keyword in user_text for keyword in ["upload", "index", "arquivo", "liste os arquivos", "quais arquivos"]):
            logger.info(f"[{self.name}] → Routing to File Manager (file-related query)")
            route_to_file_manager = True

        else:
            logger.info(f"[{self.name}] → Routing to Search Assistant (search/question query)")
            route_to_file_manager = False

        if route_to_file_manager:
            logger.info(f"[{self.name}] Running File Manager Agent...")
            async for event in self.file_manager.run_async(ctx):
                logger.info(f"[{self.name}] Event from FileManager: {event.author}")
                yield event
        else:
            logger.info(f"[{self.name}] Running Search Assistant Agent...")
            async for event in self.search_assistant.run_async(ctx):
                logger.info(f"[{self.name}] Event from SearchAssistant: {event.author}")
                yield event

        logger.info(f"[{self.name}] Orchestration complete")


