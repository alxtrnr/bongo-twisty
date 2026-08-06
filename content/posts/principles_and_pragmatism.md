+++
title = "Principles Encouraged. Pragmatism Tolerated?"
description = "Skirting the boundaries of what's acceptable to navigate risk"
date = 2026-08-06
draft = false
author = "Alexander"
images = []
+++

I have spent just over a decade on Git Hub. I'm a hobbyist. Very little if anything I've had on there has been of benefit to anyone other than myself. Microsoft's acquisition of GitHub in 2019 did not pass me by. I turned a blind eye. I think it's fair to say my patronage is of no benefit to Microsoft.

Since spring 2025 I've used Git Hub to host and publish my Hugo blog. I'm getting something for nothing. That sits well with me since it's Microsoft. It still feels a bit off though since I'm the type to shun big corp by default for all the usual reasons. 

Earlier this year I decided to make the effort to migrate my repos to a service with principles more aligned with my own. I chose [Codeberg](https://docs.codeberg.org/getting-started/what-is-codeberg/). The migration process was quick and easy since I was using Git Hub as little more than a back up facility for everything other than the blog. I was a bit wary about moving it and having to set up a different workflow for publishing so put that job on my list of things to do. 

Even though I created the workflow with the use of an LLM it took a while before I set about the task to create one that would work with [Codeberg pages](https://docs.codeberg.org/codeberg-pages/). Once I started it did not take long to come up with something that worked as intended. Before throwing in the towel with Git Hub it seemed sensible to test things out for a while with Codeberg. I set up a dual push work flow and to this day my blog is mirrored and published on both platforms. 

Then the democratic decision was made. Codeberg members voted to support a [motion](https://blog.codeberg.org/protecting-our-floss-commons-from-llms.html) that served to *"[prohibit LLM-extrusions](https://codeberg.org/Codeberg/org/commit/96fac426a32d1ba91ff879366d59bf1af54080c2)"* i.e code that has been squeezed out of an LLM.  

As is often the way I found myself close to the edge. My shortcodes, partials, layouts, webmention script, CI/CD pipelines, and bash scripts were all developed with LLM prompting. The guidelines indicate this as something that *"...might no longer be welcome on Codeberg."* However, they also say, *"...you don't need to move right away, but there might be other places that better fit your needs"*.

On the plus side I direct the LLM what to code, review outputs, test, and iterate. My blog has a genuine use case and is of value to me. It's a real blog, it's not a generated repo farm. It's not autonomous, there are no agents writing commits without my involvement. More than 99% of the writing and images are created by me. Resource usage is probably modest in absolute terms. 

I think I may be in the zone Codeberg describes as *"discouraged but tolerated."* However, if Codeberg tightens enforcement, the repo for my blog could be flagged because some of the code bears the hallmarks of LLM generation (consistent structure, verbose comments explaining obvious things etc). 

With this in mind I have mitigated the risk of being booted off the platform but in doing so have perhaps also increased my exposure to it. I now have a triple deployment approach and added [Codefloe](https://forum.codefloe.com/guidelines) into the mix. Codefloe don't share the same position as Codeberg about code written with or by LLMs. 

So my blog is now hosted and published on three platforms. 

| Platform | Domain | Role | Custom domain |
|---|---|---|---|
| Git Hub Pages | [bongotwisty.blog](https://www.bongotwisty.blog) | Primary | Yes (configured in GitHub repo settings) |
| Codeberg Pages | [bongotwisty.codeberg.page](https://bongotwisty.codeberg.page) | Mirror / backup | No (uses default Codeberg Pages URL) |
| Codefloe Pages | [bongo-twisty.bongotwisty.codefloe.page](https://bongo-twisty.bongotwisty.codefloe.page) | Contingency | No (uses default Codefloe Pages URL) |

All three pipelines build from the same main branch on push. The built in redundancy seems pretty cool to me. It's way over the top for a personal blog with very few if any regular visitors but it keeps me entertained. 

I know that Codeberg and Codefloe both need donations. I'm happy to contribute. 