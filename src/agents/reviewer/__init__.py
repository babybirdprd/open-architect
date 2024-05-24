# src/agents/reviewer/__init__.py
import time
from typing import List, Dict

from src.lib.terminal import colorize
from src.agents.reviewer.generators.code_review_generator import GeneratedCodeReview
from src.agents.reviewer.processors import review_code
from src.models import PR, Ticket
# from src.helpers.board import BoardHelper
from src.helpers.github import GHHelper


class Reviewer:
    def __init__(self, name, gh_helper: GHHelper, tasks: Dict[str, List[Ticket]]): #, board_helper: BoardHelper):
        self.name = name
        self.pr_backlog: List[PR] = []
        self.gh_helper = gh_helper
        self.tasks = tasks
        # self.board_helper = board_helper
        self.log_name = colorize(f"[{self.name} the reviewer]", bold=True, color="cyan")
        print(
            f"{self.log_name} Hi, my name is {self.name} and I'm an experienced code reviewer. I'm ready to review some bad code 🧐."
        )

    def refresh_pr_backlog(self):
        next_prs = [
            pr for pr in self.gh_helper.list_open_prs() if pr not in self.pr_backlog
        ]
        self.pr_backlog.extend(next_prs)

    # def simplify_pr(self, raw_pr: PullRequest, ticket: Ticket) -> PR:
    #     files_changed = raw_pr.get_files()

    #     files_changed_with_diffs: List[ModifiedFile] = []
    #     for file in files_changed:
    #         files_changed_with_diffs.append(
    #             ModifiedFile(
    #                 filename=file.filename,
    #                 status=file.status,
    #                 additions=file.additions,
    #                 deletions=file.deletions,
    #                 changes=file.changes,
    #                 patch=file.patch,  # This contains the diff for the file
    #             )
    #         )

    #     pr: PR = PR(
    #         id=raw_pr.number,
    #         ticket_id=ticket.id,
    #         assignee_id=ticket.assignee_id,
    #         title=raw_pr.title,
    #         description=raw_pr.body if raw_pr.body is not None else "",
    #         files_changed=files_changed_with_diffs,
    #     )

    #     return pr

    def submit_code_review(self, generated_code_review: GeneratedCodeReview):
        for comment in generated_code_review.code_review.comments:
            if not "position" in comment:
                comment["position"] = 0

        self.gh_helper.submit_code_review(generated_code_review.code_review)

        trello_ticket_id = generated_code_review.code_review.pr.ticket_id
        if (
            generated_code_review.is_valid_code
            and generated_code_review.resolves_ticket
        ):
            # self.board_helper.move_to_approved(ticket_id=trello_ticket_id)
            self.move_task(trello_ticket_id, 'Approved')
        else:
            # self.board_helper.move_to_reviewed(ticket_id=trello_ticket_id)
            self.move_task(trello_ticket_id, 'Reviewed')

    def process_pr(self):
        codebase = self.gh_helper.get_entire_codebase()

        # Get first open PR from GH that hasn't been approved yet
        pr = self.pr_backlog.pop(0)

        # Fetch the Trello ticket that corresponds to this PR
        ticket = self.get_task(task_id=pr.ticket_id)

        print(
            f'{self.log_name} I am reviewing the PR for this ticket: "{ticket.title:.30}..."'
        )
        generated_code_review = review_code(codebase=codebase, ticket=ticket, pr=pr)
        self.submit_code_review(generated_code_review=generated_code_review)
        print(
            f"{self.log_name} Finished reviewing the PR! Check it out on Github: {pr.url}"
        )

    def run(self):
        while True:
            self.refresh_pr_backlog()
            if len(self.pr_backlog) > 0:
                self.process_pr()
            time.sleep(10)
    
    def move_task(self, task_id: str, target_column: str):
        """Moves a task from its current column to the target column."""
        for column_name, tasks in self.tasks.items():
            for i, task in enumerate(tasks):
                if task.id == task_id:
                    # Remove task from its current column
                    del self.tasks[column_name][i]

                    # Add task to the target column
                    task.status = target_column
                    self.tasks[target_column].append(task)

                    # Reset drag and drop state
                    # st.session_state.drag_source = None
                    # st.experimental_set_query_params(drag_source=None, drop_target=None)
                    return
    
    def get_task(self, task_id: str) -> Ticket:
        """Gets a task from the task list."""
        for column_name, tasks in self.tasks.items():
            for i, task in enumerate(tasks):
                if task.id == task_id:
                    return task
        return None