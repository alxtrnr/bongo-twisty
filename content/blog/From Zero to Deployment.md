+++
title = "From Zero to Deployed: My Automated Hugo Workflow on Two Machines"
description = "A detailed account of my journey choosing Hugo, installing it for the first time, and building a fully automated, multi-machine deployment pipeline with Git and GitHub Actions."
date = 2025-07-07T10:00:00+01:00
draft = false
tags = ["Hugo"]
toc = false
+++

When I decided to build a new website, my goal was clear: I wanted something fast, secure, and simple to manage. My research led me to **Hugo**, a static site generator (SSG) renowned for its incredible speed and flexibility.

However, I had a significant challenge: I had next to no prior knowledge of Hugo, Git, or the automated deployment pipelines I was reading about[1][11]. This is where my journey takes a modern turn. I decided to use an LLM (Large Language Model) as my personal guide, which compressed a process that could have taken weeks of fragmented research into a focused, **six-hour sprint from start to finish**.

### The Co-Pilot in My Command Line: The Role of the LLM

LLMs often get a bad press on the IndieWeb, sometimes seen as tools that bypass genuine understanding. My experience was the opposite. The LLM didn't do the work *for* me; it enabled me to do the work *myself*. It acted as an interactive mentor that could:

*   Provide specific, context-aware commands.
*   Explain complex concepts like Git branches and submodules in simple terms.
*   Diagnose error messages and offer exact solutions.

The most remarkable outcome of this approach was the speed. The entire project—from installing Hugo for the first time to having a live site deploying automatically from two separate machines—was completed in a single evening. This entire post documents that journey, a conversation between me and my AI guide.

### Phase 1: The First Steps - Installation and Local Development

My first prompt to the LLM was simple: "How do I start with Hugo?" It guided me through the installation and the initial site creation[1][14].

```bash
# Create a new Hugo site

hugo new site my-new-website

# Navigate into the new directory

cd my-new-website

# Add a theme (typically as a Git submodule)

git init
git submodule add https://github.com/some-user/some-theme.git themes/some-theme
echo "theme = 'some-theme'" >> hugo.toml

# Start the local development server

hugo server

```

With the server running, Hugo's `LiveReload` feature instantly reflected any changes I made, creating a tight feedback loop that was essential for a beginner[2].

### Phase 2: Building the Foundation with Git and GitHub

Once my local site was working, I asked the LLM, "How do I get this on GitHub?" It provided the exact sequence of Git commands to version control my project and push it to a remote repository.

```bash
# Initialize the local repository (if not already done)

git init

# Add all files to be tracked

git add .

# Make the first commit

git commit -m "Initial commit of Hugo site"

# Connect to the remote GitHub repository and push

git remote add origin https://github.com/your-username/your-repo-name.git
git push -u origin main

```

### Phase 3: The Magic of Automation - Demystifying GitHub Actions

This was the most complex part of the project. The LLM introduced me to **GitHub Actions** and provided a complete workflow file (`.github/workflows/deploy.yaml`) to copy and paste. It explained what each section did, from installing Hugo to deploying the final `public` directory to GitHub Pages[5].

A crucial insight from the LLM was the need to configure my repository's **Settings > Pages** to use **GitHub Actions** as the build source—a small but vital step I would have otherwise missed[5].

### Phase 4: Overcoming Inevitable Errors with an AI Troubleshooter

The path wasn't perfectly smooth. When Git threw errors, the LLM became an invaluable debugger. I could paste an error message directly into the chat and get an immediate explanation and a solution.

*   **`main` vs. `master`**: When my local and remote branches didn't match, the LLM explained why and gave me the command to rename my local branch.
*   **`fatal: refusing to merge unrelated histories`**: This cryptic error was quickly deciphered. The LLM explained that my local project and the remote one didn't share a common starting point and provided the `--allow-unrelated-histories` flag as the intentional fix.

This turned moments of frustration into powerful learning opportunities.

### Phase 5: The Multi-Machine Workflow

To complete my setup, I wanted to work from a second laptop. I asked the LLM for the steps, and it provided a clear, concise plan:
1.  **Install Hugo and Git**, ensuring the versions matched my primary machine.
2.  **Clone the repository** from GitHub.
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```
3.  **Initialize the theme submodule**. The LLM highlighted this vital step, explaining that cloning a repository doesn't automatically download its submodules.
    ```bash
    git submodule update --init --recursive
    ```

My workflow is now perfectly synchronized. I `git pull` before I start working and `git push` when I'm done.

### A Note on This Post: A Human-AI Collaboration

In the spirit of transparency, this blog post is itself a product of the collaboration I've described. I provided the key topics, personal experiences, and the overall narrative structure. The LLM then did the "donkey work" of writing up the detailed explanations and formatting it all in Markdown, ready for my Hugo site. It's a real-world example of using AI to augment, not replace, the creative process.

### Conclusion

This journey has been about more than just learning Hugo; it has been an exploration into a new way of learning. The combination of Hugo's power, Git's robustness, and the 24/7 guidance of an LLM created a learning environment that was both efficient and empowering. It proves that with the right tools, anyone can tackle complex technical projects and build something they're proud of—not in weeks or months, but in a matter of hours.
```

[1]: https://gohugo.io/getting-started/quick-start/

[2]: https://gohugo.io/getting-started/usage/

[3]: https://gohugo.io/templates/introduction/

[4]: https://gohugo.io/getting-started/directory-structure/

[5]: https://gohugo.io/host-and-deploy/host-on-github-pages/

[6]: https://gohugo.io/content-management/formats/

[7]: https://gohugo.io/templates/types/

[8]: https://gohugo.io/content-management/syntax-highlighting/

[9]: https://gohugo.io/content-management/shortcodes/

[10]: https://gohugo.io/content-management/image-processing/

[11]: https://dev.to/hexadecimalsoftware/getting-started-with-hugo-a-beginners-guide-to-building-fast-websites-4a6p

[12]: https://www.geeksforgeeks.org/go-language/static-site-generation-with-hugo/

[13]: https://www.youtube.com/watch?v=5qKV4e0SgLA

[14]: https://dev.to/polluterofminds/how-to-build-and-host-a-hugo-site-gl7

[15]: https://chasemao.com/article/how-to-build-hugo-website/

[16]: http://www.testingwithmarie.com/posts/20241126-create-a-static-blog-with-hugo/

[17]: https://liamasman.com/blog/posts/2025/04/creating-a-simple-blog-with-hugo-and-netlify/

