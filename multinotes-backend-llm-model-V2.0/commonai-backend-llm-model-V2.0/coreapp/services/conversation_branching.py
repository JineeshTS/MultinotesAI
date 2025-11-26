"""
Conversation Branching Service for MultinotesAI.

This module provides:
- Create branches from any point in a conversation
- Manage conversation trees with multiple paths
- Navigate and compare different conversation branches
- Merge branches back together
- Export branch histories

WBS Item: 6.1.2 - Conversation branching
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Set

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

logger = logging.getLogger(__name__)


# =============================================================================
# Branch Configuration
# =============================================================================

class BranchStatus(Enum):
    """Status of a conversation branch."""
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    MERGED = 'merged'
    DELETED = 'deleted'


class MergeStrategy(Enum):
    """Strategies for merging branches."""
    APPEND = 'append'  # Add branch messages to main
    REPLACE = 'replace'  # Replace main with branch
    INTERLEAVE = 'interleave'  # Interleave by timestamp


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Message:
    """A single message in a conversation."""
    message_id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'parent_id': self.parent_id,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            message_id=data['message_id'],
            role=data['role'],
            content=data['content'],
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            parent_id=data.get('parent_id'),
            metadata=data.get('metadata', {}),
        )


@dataclass
class Branch:
    """A conversation branch."""
    branch_id: str
    name: str
    conversation_id: str
    parent_branch_id: Optional[str] = None
    fork_point_id: Optional[str] = None  # Message ID where branch started
    status: BranchStatus = BranchStatus.ACTIVE
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'branch_id': self.branch_id,
            'name': self.name,
            'conversation_id': self.conversation_id,
            'parent_branch_id': self.parent_branch_id,
            'fork_point_id': self.fork_point_id,
            'status': self.status.value,
            'message_count': len(self.messages),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def to_detailed_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result['messages'] = [m.to_dict() for m in self.messages]
        return result


@dataclass
class ConversationTree:
    """A conversation with multiple branches."""
    conversation_id: str
    user_id: int
    title: str
    main_branch_id: str
    branches: Dict[str, Branch] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'title': self.title,
            'main_branch_id': self.main_branch_id,
            'branch_count': len(self.branches),
            'branches': [b.to_dict() for b in self.branches.values()],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class BranchComparison:
    """Comparison between two branches."""
    branch_a_id: str
    branch_b_id: str
    common_ancestor_id: Optional[str]
    divergence_point: int  # Message index where they diverge
    branch_a_unique: List[Message]
    branch_b_unique: List[Message]
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'branch_a_id': self.branch_a_id,
            'branch_b_id': self.branch_b_id,
            'common_ancestor_id': self.common_ancestor_id,
            'divergence_point': self.divergence_point,
            'branch_a_unique_count': len(self.branch_a_unique),
            'branch_b_unique_count': len(self.branch_b_unique),
            'similarity_score': round(self.similarity_score, 3),
        }


# =============================================================================
# Conversation Branching Service
# =============================================================================

class ConversationBranchingService:
    """
    Service for managing conversation branches.

    Usage:
        service = ConversationBranchingService()

        # Create a new conversation
        conv = service.create_conversation(user_id=1, title="AI Discussion")

        # Add messages
        service.add_message(conv.conversation_id, "main", "user", "Hello")
        service.add_message(conv.conversation_id, "main", "assistant", "Hi!")

        # Create a branch from a specific message
        branch = service.create_branch(
            conversation_id=conv.conversation_id,
            from_message_id="msg_123",
            name="Alternative approach"
        )
    """

    def __init__(self):
        self._conversations: Dict[str, ConversationTree] = {}

    # -------------------------------------------------------------------------
    # Conversation Management
    # -------------------------------------------------------------------------

    def create_conversation(
        self,
        user_id: int,
        title: str = "New Conversation",
        initial_messages: List[Dict[str, str]] = None,
    ) -> ConversationTree:
        """Create a new conversation with a main branch."""
        conversation_id = str(uuid.uuid4())
        main_branch_id = str(uuid.uuid4())

        # Create main branch
        main_branch = Branch(
            branch_id=main_branch_id,
            name="main",
            conversation_id=conversation_id,
        )

        # Add initial messages if provided
        if initial_messages:
            for msg_data in initial_messages:
                message = Message(
                    message_id=str(uuid.uuid4()),
                    role=msg_data.get('role', 'user'),
                    content=msg_data.get('content', ''),
                    parent_id=main_branch.messages[-1].message_id if main_branch.messages else None,
                )
                main_branch.messages.append(message)

        # Create conversation tree
        conversation = ConversationTree(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            main_branch_id=main_branch_id,
            branches={main_branch_id: main_branch},
        )

        self._conversations[conversation_id] = conversation
        self._cache_conversation(conversation)

        logger.info(f"Created conversation {conversation_id} for user {user_id}")

        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[ConversationTree]:
        """Get a conversation by ID."""
        if conversation_id in self._conversations:
            return self._conversations[conversation_id]

        # Check cache
        cached = cache.get(f"conversation_tree:{conversation_id}")
        if cached:
            self._conversations[conversation_id] = cached
            return cached

        return None

    def list_conversations(
        self,
        user_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List conversations for a user."""
        conversations = [
            c for c in self._conversations.values()
            if c.user_id == user_id
        ]

        # Sort by updated_at descending
        conversations.sort(key=lambda c: c.updated_at, reverse=True)

        return [c.to_dict() for c in conversations[:limit]]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its branches."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            cache.delete(f"conversation_tree:{conversation_id}")
            return True
        return False

    # -------------------------------------------------------------------------
    # Branch Management
    # -------------------------------------------------------------------------

    def create_branch(
        self,
        conversation_id: str,
        from_message_id: str,
        name: str = None,
        copy_subsequent: bool = False,
    ) -> Optional[Branch]:
        """
        Create a new branch from a specific message.

        Args:
            conversation_id: The conversation to branch
            from_message_id: Message ID to branch from
            name: Name for the new branch
            copy_subsequent: Whether to copy messages after fork point

        Returns:
            The created Branch
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        # Find the message and its branch
        source_branch = None
        fork_index = -1

        for branch in conversation.branches.values():
            for i, msg in enumerate(branch.messages):
                if msg.message_id == from_message_id:
                    source_branch = branch
                    fork_index = i
                    break
            if source_branch:
                break

        if not source_branch or fork_index < 0:
            logger.error(f"Message {from_message_id} not found in conversation")
            return None

        # Create new branch
        branch_id = str(uuid.uuid4())
        branch_name = name or f"Branch {len(conversation.branches)}"

        new_branch = Branch(
            branch_id=branch_id,
            name=branch_name,
            conversation_id=conversation_id,
            parent_branch_id=source_branch.branch_id,
            fork_point_id=from_message_id,
        )

        # Copy messages up to and including fork point
        for i, msg in enumerate(source_branch.messages):
            if i <= fork_index:
                new_msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                    parent_id=new_branch.messages[-1].message_id if new_branch.messages else None,
                    metadata={**msg.metadata, 'copied_from': msg.message_id},
                )
                new_branch.messages.append(new_msg)

        # Optionally copy subsequent messages
        if copy_subsequent:
            for i, msg in enumerate(source_branch.messages):
                if i > fork_index:
                    new_msg = Message(
                        message_id=str(uuid.uuid4()),
                        role=msg.role,
                        content=msg.content,
                        created_at=msg.created_at,
                        parent_id=new_branch.messages[-1].message_id,
                        metadata={**msg.metadata, 'copied_from': msg.message_id},
                    )
                    new_branch.messages.append(new_msg)

        conversation.branches[branch_id] = new_branch
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)

        logger.info(f"Created branch {branch_id} in conversation {conversation_id}")

        return new_branch

    def get_branch(
        self,
        conversation_id: str,
        branch_id: str,
    ) -> Optional[Branch]:
        """Get a specific branch."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        return conversation.branches.get(branch_id)

    def list_branches(
        self,
        conversation_id: str,
    ) -> List[Dict[str, Any]]:
        """List all branches in a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []

        return [b.to_dict() for b in conversation.branches.values()]

    def rename_branch(
        self,
        conversation_id: str,
        branch_id: str,
        new_name: str,
    ) -> bool:
        """Rename a branch."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        branch = conversation.branches.get(branch_id)
        if not branch:
            return False

        branch.name = new_name
        branch.updated_at = datetime.now()
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)
        return True

    def archive_branch(
        self,
        conversation_id: str,
        branch_id: str,
    ) -> bool:
        """Archive a branch."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        branch = conversation.branches.get(branch_id)
        if not branch:
            return False

        if branch_id == conversation.main_branch_id:
            logger.error("Cannot archive main branch")
            return False

        branch.status = BranchStatus.ARCHIVED
        branch.updated_at = datetime.now()
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)
        return True

    def delete_branch(
        self,
        conversation_id: str,
        branch_id: str,
    ) -> bool:
        """Delete a branch."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        if branch_id == conversation.main_branch_id:
            logger.error("Cannot delete main branch")
            return False

        if branch_id in conversation.branches:
            del conversation.branches[branch_id]
            conversation.updated_at = datetime.now()
            self._cache_conversation(conversation)
            return True

        return False

    # -------------------------------------------------------------------------
    # Message Management
    # -------------------------------------------------------------------------

    def add_message(
        self,
        conversation_id: str,
        branch_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Message]:
        """Add a message to a branch."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        branch = conversation.branches.get(branch_id)
        if not branch:
            return None

        message = Message(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            parent_id=branch.messages[-1].message_id if branch.messages else None,
            metadata=metadata or {},
        )

        branch.messages.append(message)
        branch.updated_at = datetime.now()
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)

        return message

    def get_messages(
        self,
        conversation_id: str,
        branch_id: str,
        limit: int = None,
        after_message_id: str = None,
    ) -> List[Message]:
        """Get messages from a branch."""
        branch = self.get_branch(conversation_id, branch_id)
        if not branch:
            return []

        messages = branch.messages

        # Filter after specific message
        if after_message_id:
            found = False
            filtered = []
            for msg in messages:
                if found:
                    filtered.append(msg)
                if msg.message_id == after_message_id:
                    found = True
            messages = filtered

        # Apply limit
        if limit:
            messages = messages[-limit:]

        return messages

    def edit_message(
        self,
        conversation_id: str,
        branch_id: str,
        message_id: str,
        new_content: str,
        create_branch: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Edit a message in a branch.

        If create_branch is True, creates a new branch from the edit point.
        """
        branch = self.get_branch(conversation_id, branch_id)
        if not branch:
            return None

        # Find message index
        msg_index = -1
        for i, msg in enumerate(branch.messages):
            if msg.message_id == message_id:
                msg_index = i
                break

        if msg_index < 0:
            return None

        if create_branch:
            # Create a new branch with the edit
            new_branch = self.create_branch(
                conversation_id=conversation_id,
                from_message_id=branch.messages[msg_index - 1].message_id if msg_index > 0 else message_id,
                name=f"Edit of message {message_id[:8]}",
            )

            if new_branch:
                # Add edited message to new branch
                edited_msg = self.add_message(
                    conversation_id=conversation_id,
                    branch_id=new_branch.branch_id,
                    role=branch.messages[msg_index].role,
                    content=new_content,
                    metadata={'edited_from': message_id},
                )

                return {
                    'new_branch': new_branch.to_dict(),
                    'edited_message': edited_msg.to_dict() if edited_msg else None,
                }
        else:
            # Edit in place
            branch.messages[msg_index].content = new_content
            branch.messages[msg_index].metadata['edited_at'] = datetime.now().isoformat()
            branch.updated_at = datetime.now()

            conversation = self.get_conversation(conversation_id)
            if conversation:
                conversation.updated_at = datetime.now()
                self._cache_conversation(conversation)

            return {
                'edited_message': branch.messages[msg_index].to_dict(),
            }

        return None

    def delete_message(
        self,
        conversation_id: str,
        branch_id: str,
        message_id: str,
        delete_subsequent: bool = True,
    ) -> bool:
        """Delete a message and optionally subsequent messages."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        branch = conversation.branches.get(branch_id)
        if not branch:
            return False

        msg_index = -1
        for i, msg in enumerate(branch.messages):
            if msg.message_id == message_id:
                msg_index = i
                break

        if msg_index < 0:
            return False

        if delete_subsequent:
            branch.messages = branch.messages[:msg_index]
        else:
            branch.messages.pop(msg_index)

        branch.updated_at = datetime.now()
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)
        return True

    # -------------------------------------------------------------------------
    # Branch Comparison and Merging
    # -------------------------------------------------------------------------

    def compare_branches(
        self,
        conversation_id: str,
        branch_a_id: str,
        branch_b_id: str,
    ) -> Optional[BranchComparison]:
        """Compare two branches."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        branch_a = conversation.branches.get(branch_a_id)
        branch_b = conversation.branches.get(branch_b_id)

        if not branch_a or not branch_b:
            return None

        # Find common ancestor (divergence point)
        common_ancestor_id = None
        divergence_point = 0

        for i, (msg_a, msg_b) in enumerate(zip(branch_a.messages, branch_b.messages)):
            if msg_a.content == msg_b.content and msg_a.role == msg_b.role:
                common_ancestor_id = msg_a.message_id
                divergence_point = i + 1
            else:
                break

        # Get unique messages
        branch_a_unique = branch_a.messages[divergence_point:]
        branch_b_unique = branch_b.messages[divergence_point:]

        # Calculate similarity
        total_unique = len(branch_a_unique) + len(branch_b_unique)
        total_common = divergence_point
        similarity = total_common / (total_common + total_unique) if (total_common + total_unique) > 0 else 1.0

        return BranchComparison(
            branch_a_id=branch_a_id,
            branch_b_id=branch_b_id,
            common_ancestor_id=common_ancestor_id,
            divergence_point=divergence_point,
            branch_a_unique=branch_a_unique,
            branch_b_unique=branch_b_unique,
            similarity_score=similarity,
        )

    def merge_branch(
        self,
        conversation_id: str,
        source_branch_id: str,
        target_branch_id: str,
        strategy: MergeStrategy = MergeStrategy.APPEND,
    ) -> bool:
        """Merge one branch into another."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        source = conversation.branches.get(source_branch_id)
        target = conversation.branches.get(target_branch_id)

        if not source or not target:
            return False

        # Find divergence point
        comparison = self.compare_branches(
            conversation_id, source_branch_id, target_branch_id
        )

        if not comparison:
            return False

        if strategy == MergeStrategy.APPEND:
            # Append unique source messages to target
            for msg in comparison.branch_a_unique:
                new_msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=msg.role,
                    content=msg.content,
                    parent_id=target.messages[-1].message_id if target.messages else None,
                    metadata={**msg.metadata, 'merged_from': source_branch_id},
                )
                target.messages.append(new_msg)

        elif strategy == MergeStrategy.REPLACE:
            # Replace target messages after divergence with source
            target.messages = target.messages[:comparison.divergence_point]
            for msg in comparison.branch_a_unique:
                new_msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=msg.role,
                    content=msg.content,
                    parent_id=target.messages[-1].message_id if target.messages else None,
                    metadata={**msg.metadata, 'merged_from': source_branch_id},
                )
                target.messages.append(new_msg)

        elif strategy == MergeStrategy.INTERLEAVE:
            # Interleave messages by timestamp
            all_unique = (
                [(m, 'a') for m in comparison.branch_a_unique] +
                [(m, 'b') for m in comparison.branch_b_unique]
            )
            all_unique.sort(key=lambda x: x[0].created_at)

            target.messages = target.messages[:comparison.divergence_point]
            for msg, source_branch in all_unique:
                new_msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=msg.role,
                    content=msg.content,
                    parent_id=target.messages[-1].message_id if target.messages else None,
                    metadata={**msg.metadata, 'merged_from': source_branch_id if source_branch == 'a' else target_branch_id},
                )
                target.messages.append(new_msg)

        # Mark source as merged
        source.status = BranchStatus.MERGED
        source.updated_at = datetime.now()
        target.updated_at = datetime.now()
        conversation.updated_at = datetime.now()

        self._cache_conversation(conversation)

        logger.info(f"Merged branch {source_branch_id} into {target_branch_id}")
        return True

    # -------------------------------------------------------------------------
    # Branch Navigation
    # -------------------------------------------------------------------------

    def get_branch_tree(
        self,
        conversation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the branch tree structure."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        def build_tree(branch_id: str, visited: Set[str] = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()

            if branch_id in visited:
                return None

            visited.add(branch_id)

            branch = conversation.branches.get(branch_id)
            if not branch:
                return None

            # Find child branches
            children = []
            for b in conversation.branches.values():
                if b.parent_branch_id == branch_id:
                    child_tree = build_tree(b.branch_id, visited)
                    if child_tree:
                        children.append(child_tree)

            return {
                'branch_id': branch_id,
                'name': branch.name,
                'status': branch.status.value,
                'message_count': len(branch.messages),
                'fork_point_id': branch.fork_point_id,
                'children': children,
            }

        return build_tree(conversation.main_branch_id)

    def get_full_context(
        self,
        conversation_id: str,
        branch_id: str,
        include_parent_history: bool = True,
    ) -> List[Message]:
        """Get full message context for a branch, optionally including parent history."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []

        branch = conversation.branches.get(branch_id)
        if not branch:
            return []

        if not include_parent_history or not branch.parent_branch_id:
            return branch.messages

        # Build full history by traversing parent branches
        history = []
        current_branch = branch

        while current_branch:
            if current_branch.fork_point_id:
                # Get messages up to fork point from parent
                parent = conversation.branches.get(current_branch.parent_branch_id)
                if parent:
                    for msg in parent.messages:
                        history.insert(0, msg)
                        if msg.message_id == current_branch.fork_point_id:
                            break
                current_branch = parent
            else:
                break

        # Add current branch messages (excluding duplicates)
        existing_ids = {m.message_id for m in history}
        for msg in branch.messages:
            if msg.message_id not in existing_ids:
                history.append(msg)

        return history

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def export_branch(
        self,
        conversation_id: str,
        branch_id: str,
        format: str = 'json',
    ) -> Optional[Any]:
        """Export a branch in various formats."""
        branch = self.get_branch(conversation_id, branch_id)
        if not branch:
            return None

        if format == 'json':
            return branch.to_detailed_dict()

        elif format == 'markdown':
            lines = [f"# {branch.name}\n"]
            for msg in branch.messages:
                role_prefix = "**User:**" if msg.role == 'user' else "**Assistant:**"
                lines.append(f"{role_prefix}\n{msg.content}\n")
            return '\n'.join(lines)

        elif format == 'text':
            lines = []
            for msg in branch.messages:
                role_prefix = "User: " if msg.role == 'user' else "Assistant: "
                lines.append(f"{role_prefix}{msg.content}")
            return '\n\n'.join(lines)

        return None

    def export_conversation(
        self,
        conversation_id: str,
        format: str = 'json',
        include_all_branches: bool = True,
    ) -> Optional[Any]:
        """Export entire conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        if format == 'json':
            result = conversation.to_dict()
            if include_all_branches:
                result['branches_detail'] = [
                    b.to_detailed_dict() for b in conversation.branches.values()
                ]
            return result

        elif format == 'markdown':
            lines = [f"# {conversation.title}\n"]

            if include_all_branches:
                for branch in conversation.branches.values():
                    lines.append(f"\n## Branch: {branch.name}\n")
                    for msg in branch.messages:
                        role_prefix = "**User:**" if msg.role == 'user' else "**Assistant:**"
                        lines.append(f"{role_prefix}\n{msg.content}\n")
            else:
                main_branch = conversation.branches.get(conversation.main_branch_id)
                if main_branch:
                    for msg in main_branch.messages:
                        role_prefix = "**User:**" if msg.role == 'user' else "**Assistant:**"
                        lines.append(f"{role_prefix}\n{msg.content}\n")

            return '\n'.join(lines)

        return None

    # -------------------------------------------------------------------------
    # Caching
    # -------------------------------------------------------------------------

    def _cache_conversation(self, conversation: ConversationTree):
        """Cache conversation state."""
        cache.set(
            f"conversation_tree:{conversation.conversation_id}",
            conversation,
            timeout=86400,
        )


# =============================================================================
# Database Integration
# =============================================================================

class ConversationBranchingDatabaseService(ConversationBranchingService):
    """
    Database-backed version of ConversationBranchingService.

    Integrates with Django models for persistence.
    """

    def create_conversation_from_prompt(
        self,
        prompt_id: int,
    ) -> Optional[ConversationTree]:
        """Create a conversation tree from an existing Prompt model."""
        try:
            from coreapp.models import Prompt, PromptResponse

            prompt = Prompt.objects.select_related('user').get(id=prompt_id)

            # Create conversation
            conversation = self.create_conversation(
                user_id=prompt.user.id,
                title=prompt.prompt[:50] + '...' if len(prompt.prompt) > 50 else prompt.prompt,
            )

            # Add initial user message
            self.add_message(
                conversation_id=conversation.conversation_id,
                branch_id=conversation.main_branch_id,
                role='user',
                content=prompt.prompt,
                metadata={'prompt_id': prompt_id},
            )

            # Add responses
            responses = PromptResponse.objects.filter(prompt=prompt).order_by('created_at')
            for response in responses:
                self.add_message(
                    conversation_id=conversation.conversation_id,
                    branch_id=conversation.main_branch_id,
                    role='assistant',
                    content=response.response,
                    metadata={
                        'response_id': response.id,
                        'llm_id': response.llm_id,
                    },
                )

            return conversation

        except Exception as e:
            logger.exception(f"Failed to create conversation from prompt: {e}")
            return None


# =============================================================================
# Singleton Instance
# =============================================================================

conversation_branching_service = ConversationBranchingService()
conversation_branching_db_service = ConversationBranchingDatabaseService()
