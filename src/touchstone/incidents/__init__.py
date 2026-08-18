"""The corpus: the generator, its ten renderers, and the deletion path.

⛔ Nothing here imports the agent, the SDK or LangGraph. The suite has to be buildable — and
re-buildable, byte for byte — on a machine with no model access at all, or a benchmark hash
means "what this laptop produced" rather than "what the seed produced".
"""
