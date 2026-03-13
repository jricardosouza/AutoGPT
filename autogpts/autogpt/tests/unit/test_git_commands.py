import pytest
from git.exc import GitCommandError
from git.repo.base import Repo
from unittest.mock import MagicMock

from autogpt.agents.agent import Agent
from autogpt.agents.utils.exceptions import CommandExecutionError
from autogpt.commands.git_operations import clone_repository, create_repository


@pytest.fixture
def mock_clone_from(mocker):
    return mocker.patch.object(Repo, "clone_from")


def test_clone_auto_gpt_repository(workspace, mock_clone_from, agent: Agent):
    mock_clone_from.return_value = None

    repo = "github.com/Significant-Gravitas/Auto-GPT.git"
    scheme = "https://"
    url = scheme + repo
    clone_path = workspace.get_path("auto-gpt-repo")

    expected_output = f"Cloned {url} to {clone_path}"

    clone_result = clone_repository(url=url, clone_path=clone_path, agent=agent)

    assert clone_result == expected_output
    mock_clone_from.assert_called_once_with(
        url=f"{scheme}{agent.legacy_config.github_username}:{agent.legacy_config.github_api_key}@{repo}",  # noqa: E501
        to_path=clone_path,
    )


def test_clone_repository_error(workspace, mock_clone_from, agent: Agent):
    url = "https://github.com/this-repository/does-not-exist.git"
    clone_path = workspace.get_path("does-not-exist")

    mock_clone_from.side_effect = GitCommandError(
        "clone", "fatal: repository not found", ""
    )

    with pytest.raises(CommandExecutionError):
        clone_repository(url=url, clone_path=clone_path, agent=agent)


@pytest.fixture
def mock_requests_post(mocker):
    return mocker.patch("autogpt.commands.git_operations.requests.post")


def test_create_repository_success(mock_requests_post, agent: Agent):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "html_url": "https://github.com/user/new-repo",
    }
    mock_requests_post.return_value = mock_response

    result = create_repository(name="new-repo", agent=agent)

    assert result == "Created private repository 'new-repo' at https://github.com/user/new-repo"
    mock_requests_post.assert_called_once_with(
        "https://api.github.com/user/repos",
        headers={
            "Authorization": f"token {agent.legacy_config.github_api_key}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={
            "name": "new-repo",
            "private": True,
        },
        timeout=30,
    )


def test_create_repository_error(mock_requests_post, agent: Agent):
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {
        "message": "Repository creation failed: name already exists on this account",
    }
    mock_requests_post.return_value = mock_response

    with pytest.raises(CommandExecutionError):
        create_repository(name="existing-repo", agent=agent)


def test_create_repository_network_error(mock_requests_post, agent: Agent):
    import requests

    mock_requests_post.side_effect = requests.ConnectionError("Network error")

    with pytest.raises(CommandExecutionError):
        create_repository(name="new-repo", agent=agent)
