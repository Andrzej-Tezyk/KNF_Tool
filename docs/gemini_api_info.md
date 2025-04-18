TO IMPLEMENT:

1) context cashing for uploaded files (if free) -> https://ai.google.dev/gemini-api/docs/caching?lang=python
2) configuration options
- temperature
- presencePenalty, frequencyPenalty -> increase vocabularity
3) a monitored channel for users to share feedback


topK: The topK parameter changes how the model selects tokens for output. A topK of 1 means the selected token is the most probable among all the tokens in the model's vocabulary (also called greedy decoding), while a topK of 3 means that the next token is selected from among the 3 most probable using the temperature. For each token selection step, the topK tokens with the highest probabilities are sampled. Tokens are then further filtered based on topP with the final token selected using temperature sampling.

topP: The topP parameter changes how the model selects tokens for output. Tokens are selected from the most to least probable until the sum of their probabilities equals the topP value. For example, if tokens A, B, and C have a probability of 0.3, 0.2, and 0.1 and the topP value is 0.5, then the model will select either A or B as the next token by using the temperature and exclude C as a candidate. The default topP value is 0.95.

stop_sequences: Set a stop sequence to tell the model to stop generating content. A stop sequence can be any sequence of characters. Try to avoid using a sequence of characters that may appear in the generated content.

- top, topK -> how do they affect results??? 
- safety settings -> are they needed???




# Long context -> provides additional learning capabilities to enchant answers


- 1-million-token context window = short term memory (amount of tokens that could be passed to the model at one time)

- all the messages in conversation -> context

- ways to work with context limits:
 	> deleting oldest messages
 	> summarize old messages
	> RAG + semantic search to move data into vector database
	> filter certain words/characters

- many-shot approach -> make a model solve many (up to thousands similar tasks) before passing your task
	> similar performance as fine-tuned models

- do NOT put not needed info into context -> 



- context cashing (long context optimization method)
	> you can choose how long you want the cache to exist before the tokens are automatically deleted -> TTL (time to live) = default 1h
	> good for repeating prompts
	> Context caching is only available for stable models with fixed versions (for example, gemini-1.5-pro-001). You must include the version postfix (for example, the -001 in gemini-1.5-pro-001).
	> 32,768 min tokens for caching
	> model doesn't make any distinction between cached tokens and regular input tokens

is particularly well suited to scenarios where an initial context is referenced repeatedly by shorter requests:
	> chatbots with extensive system instructions
	> repetitive analysis of lengthy video files
	> recurring queries against large document sets (+++)
	> frequent code repository analysis or bug fixing


The following steps are recommended when building applications with LLMs:
- Understanding the safety risks of your application
- Considering adjustments to mitigate safety risks
- Performing safety testing appropriate to your use case
- Soliciting feedback from users and monitoring usage

"A good way to begin exploring potential safety risks is to research your end users, and others who might be affected by your application's results. This can take many forms including researching state of the art studies in your app domain, observing how people are using similar apps, or running a user study, survey, or conducting informal interviews with potential users."

For example, when designing an application consider:

- Tuning the model output to better reflect what is acceptable in your application context. Tuning can make the output of the model more predictable and consistent and therefore can help mitigate certain risks.
- Providing an input method that facilities safer outputs. The exact input you give to an LLM can make a difference in the quality of the output. Experimenting with input prompts to find what works most safely in your use-case is well worth the effort, as you can then provide a UX that facilitates it. For example, you could restrict users to choose only from a drop-down list of input prompts, or offer pop-up suggestions with descriptive phrases which you've found perform safely in your application context.
- Blocking unsafe inputs and filtering output before it is shown to the user. In simple situations, blocklists can be used to identify and block unsafe words or phrases in prompts or responses, or require human reviewers to manually alter or block such content.
- Using trained classifiers to label each prompt with potential harms or adversarial signals. Different strategies can then be employed on how to handle the request based on the type of harm detected. For example, If the input is overtly adversarial or abusive in nature, it could be blocked and instead output a pre-scripted response.
- Putting safeguards in place against deliberate misuse such as assigning each user a unique ID and imposing a limit on the volume of user queries that can be submitted in a given period. Another safeguard is to try and protect against possible prompt injection. Prompt injection, much like SQL injection, is a way for malicious users to design an input prompt that manipulates the output of the model, for example, by sending an input prompt that instructs the model to ignore any previous examples. See the Generative AI Prohibited Use Policy for details about deliberate misuse.
- Adjusting functionality to something that is inherently lower risk. Tasks that are narrower in scope (e.g., extracting keywords from passages of text) or that have greater human oversight (e.g., generating short-form content that will be reviewed by a human), often pose a lower risk. So for instance, instead of creating an application to write an email reply from scratch, you might instead limit it to expanding on an outline or suggesting alternative phrasings.

Adjusting functionality to something that is inherently lower risk. Tasks that are narrower in scope (e.g., extracting keywords from passages of text) or that have greater human oversight (e.g., generating short-form content that will be reviewed by a human), often pose a lower risk. So for instance, instead of creating an application to write an email reply from scratch, you might instead limit it to expanding on an outline or suggesting alternative phrasings.

Note: Automatically blocking based on a static list can have unintended results such as targeting a particular group that commonly uses vocabulary in the blocklist.


Two kinds of testing are particularly useful for AI applications:

- Safety benchmarking -> designing safety metrics that reflect the ways your application could be unsafe in the context of how it is likely to get used, then testing how well your application performs on the metrics using evaluation datasets. It's good practice to think about the minimum acceptable levels of safety metrics before testing so that:
	1) you can evaluate the test results against those expectations,
	2) you can gather the evaluation dataset based on the tests that evaluate the metrics you care about most.

	(!!!) Beware of over-relying on “off the shelf” approaches as it's likely you'll need to build your own testing datasets using human raters to fully suit your application's context

- Adversarial testing involves proactively trying to break your application. For adversarial tests, select test data that is most likely to elicit problematic output from the model. It should also include diversity in the different dimensions of a sentence such as structure, meaning and length.


Note: LLMs are known to sometimes produce different outputs for the same input prompt. Multiple rounds of testing may be needed to catch more of the problematic outputs.


Fine tuning

- Your training data should be structured as examples with prompt inputs and expected response outputs.
- The goal is to teach the model to mimic the wanted behavior or task, by giving it many examples illustrating that behavior or task.
- The examples included in your dataset should match your expected production traffic. If your dataset contains specific formatting, keywords, instructions, or information, the production data should be formatted in the same way and contain the same instructions.
- You can fine-tune a model with as little as 20 examples. Additional data generally improves the quality of the responses. You should target between 100 and 500 examples, depending on your application.

	> Classification	100+
	> Summarization		100-500+
	> Document search	100+

