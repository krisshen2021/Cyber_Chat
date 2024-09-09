const cheatsheets = [
    {
        "name": "Git",
        "content": [
            {
                "category": "Basic Commands",
                "subcategories": [
                    {
                        "name": "Repository Setup",
                        "commands": [
                            { "key": "git init", "description": "Initialize a new Git repository" },
                            { "key": "git clone <url>", "description": "Clone a repository from a remote source" }
                        ]
                    },
                    {
                        "name": "Staging and Committing",
                        "commands": [
                            { "key": "git add <file>", "description": "Add file to staging area" },
                            { "key": "git add .", "description": "Add all changes to staging area" },
                            { "key": "git commit -m \"<message>\"", "description": "Commit staged changes with a message" },
                            { "key": "git commit -am \"<message>\"", "description": "Add changes and commit in one step" }
                        ]
                    },
                    {
                        "name": "Status and History",
                        "commands": [
                            { "key": "git status", "description": "Show the working tree status" },
                            { "key": "git log", "description": "Show commit logs" },
                            { "key": "git log --oneline", "description": "Show commit logs in one line format" }
                        ]
                    }
                ]
            },
            {
                "category": "Branching and Merging",
                "subcategories": [
                    {
                        "name": "Branch Management",
                        "commands": [
                            { "key": "git branch", "description": "List branches" },
                            { "key": "git branch <name>", "description": "Create a new branch" },
                            { "key": "git checkout <branch>", "description": "Switch to a branch" },
                            { "key": "git checkout -b <name>", "description": "Create and switch to a new branch" },
                            { "key": "git branch -d <name>", "description": "Delete a branch" }
                        ]
                    },
                    {
                        "name": "Merging",
                        "commands": [
                            { "key": "git merge <branch>", "description": "Merge a branch into the current branch" },
                            { "key": "git mergetool", "description": "Run merge conflict resolution tools" }
                        ]
                    },
                    {
                        "name": "Rebasing",
                        "commands": [
                            { "key": "git rebase <branch>", "description": "Rebase current branch onto another branch" },
                            { "key": "git rebase -i <commit>", "description": "Interactive rebase" }
                        ]
                    }
                ]
            },
            {
                "category": "Remote Repositories",
                "subcategories": [
                    {
                        "name": "Remote Management",
                        "commands": [
                            { "key": "git remote", "description": "List remote repositories" },
                            { "key": "git remote add <name> <url>", "description": "Add a new remote repository" },
                            { "key": "git remote remove <name>", "description": "Remove a remote repository" }
                        ]
                    },
                    {
                        "name": "Fetching and Pulling",
                        "commands": [
                            { "key": "git fetch <remote>", "description": "Download objects and refs from remote" },
                            { "key": "git pull <remote> <branch>", "description": "Fetch and merge changes from remote" }
                        ]
                    },
                    {
                        "name": "Pushing",
                        "commands": [
                            { "key": "git push <remote> <branch>", "description": "Push local changes to remote" },
                            { "key": "git push -u <remote> <branch>", "description": "Push and set upstream branch" }
                        ]
                    }
                ]
            },
            {
                "category": "Inspection and Comparison",
                "subcategories": [
                    {
                        "name": "Diff",
                        "commands": [
                            { "key": "git diff", "description": "Show changes between working directory and staging area" },
                            { "key": "git diff --staged", "description": "Show changes between staging area and last commit" },
                            { "key": "git diff <commit1> <commit2>", "description": "Show changes between two commits" }
                        ]
                    },
                    {
                        "name": "Blame",
                        "commands": [
                            { "key": "git blame <file>", "description": "Show who last modified each line of a file" }
                        ]
                    },
                    {
                        "name": "Stashing",
                        "commands": [
                            { "key": "git stash", "description": "Stash changes in working directory" },
                            { "key": "git stash list", "description": "List stashed changes" },
                            { "key": "git stash apply", "description": "Apply stashed changes" },
                            { "key": "git stash pop", "description": "Apply and remove stashed changes" },
                            { "key": "git stash drop", "description": "Remove a specific stash" }
                        ]
                    }
                ]
            },
            {
                "category": "Configuration",
                "subcategories": [
                    {
                        "name": "User Settings",
                        "commands": [
                            { "key": "git config --global user.name \"<name>\"", "description": "Set global username" },
                            { "key": "git config --global user.email \"<email>\"", "description": "Set global email" }
                        ]
                    },
                    {
                        "name": "Aliases",
                        "commands": [
                            { "key": "git config --global alias.<alias-name> <git-command>", "description": "Create a shortcut for a Git command" }
                        ]
                    },
                    {
                        "name": "Viewing Config",
                        "commands": [
                            { "key": "git config --list", "description": "List all configuration settings" },
                            { "key": "git config --global --edit", "description": "Open global config file in text editor" }
                        ]
                    }
                ]
            }
        ]
    },
    {
        "name": "Tmux",
        "content": [
            {
                "category": "Session Management",
                "subcategories": [
                    {
                        "name": "Creating and Attaching",
                        "commands": [
                            { "key": "tmux", "description": "Start a new session" },
                            { "key": "tmux new -s <name>", "description": "Start a new session with a name" },
                            { "key": "tmux attach -t <name>", "description": "Attach to an existing session" },
                            { "key": "tmux ls", "description": "List all sessions" }
                        ]
                    },
                    {
                        "name": "Detaching and Killing",
                        "commands": [
                            { "key": "Ctrl-b d", "description": "Detach from current session" },
                            { "key": "tmux kill-session -t <name>", "description": "Kill a specific session" }
                        ]
                    }
                ]
            },
            {
                "category": "Window Management",
                "subcategories": [
                    {
                        "name": "Creating and Navigating",
                        "commands": [
                            { "key": "Ctrl-b c", "description": "Create a new window" },
                            { "key": "Ctrl-b <number>", "description": "Switch to window by number" },
                            { "key": "Ctrl-b n", "description": "Move to next window" },
                            { "key": "Ctrl-b p", "description": "Move to previous window" }
                        ]
                    },
                    {
                        "name": "Renaming and Closing",
                        "commands": [
                            { "key": "Ctrl-b ,", "description": "Rename current window" },
                            { "key": "Ctrl-b &", "description": "Close current window" }
                        ]
                    }
                ]
            },
            {
                "category": "Pane Management",
                "subcategories": [
                    {
                        "name": "Splitting Panes",
                        "commands": [
                            { "key": "Ctrl-b %", "description": "Split pane vertically" },
                            { "key": "Ctrl-b \"", "description": "Split pane horizontally" }
                        ]
                    },
                    {
                        "name": "Navigating Panes",
                        "commands": [
                            { "key": "Ctrl-b <arrow key>", "description": "Move to pane in the direction of arrow key" },
                            { "key": "Ctrl-b o", "description": "Cycle through panes" },
                            { "key": "Ctrl-b x", "description": "Close current pane" }
                        ]
                    }
                ]
            }
        ]
    },
    {
        "name": "Docker",
        "content": [
            {
                "category": "Container Management",
                "subcategories": [
                    {
                        "name": "Running Containers",
                        "commands": [
                            { "key": "docker run <image>", "description": "Run a container from an image" },
                            { "key": "docker run -d <image>", "description": "Run container in detached mode" },
                            { "key": "docker start <container>", "description": "Start a stopped container" },
                            { "key": "docker stop <container>", "description": "Stop a running container" }
                        ]
                    },
                    {
                        "name": "Container Information",
                        "commands": [
                            { "key": "docker ps", "description": "List running containers" },
                            { "key": "docker ps -a", "description": "List all containers" },
                            { "key": "docker logs <container>", "description": "View container logs" }
                        ]
                    }
                ]
            },
            {
                "category": "Image Management",
                "subcategories": [
                    {
                        "name": "Working with Images",
                        "commands": [
                            { "key": "docker images", "description": "List all images" },
                            { "key": "docker pull <image>", "description": "Pull an image from a registry" },
                            { "key": "docker build -t <name> .", "description": "Build an image from a Dockerfile" },
                            { "key": "docker rmi <image>", "description": "Remove an image" }
                        ]
                    }
                ]
            },
            {
                "category": "Docker Compose",
                "subcategories": [
                    {
                        "name": "Basic Commands",
                        "commands": [
                            { "key": "docker-compose up", "description": "Create and start containers" },
                            { "key": "docker-compose down", "description": "Stop and remove containers" },
                            { "key": "docker-compose ps", "description": "List containers" },
                            { "key": "docker-compose logs", "description": "View output from containers" }
                        ]
                    }
                ]
            }
        ]
    }
];
window.cheatsheets = cheatsheets;