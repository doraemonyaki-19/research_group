# Contributing to ResearchGroup

Thank you for your interest in contributing to the ResearchGroup framework!

## Research Principles

ResearchGroup is designed to study the impact of hierarchical multi-agent architectures on scientific reasoning and optimization tasks. All contributions should align with the core research principles:
- **Reproducibility:** All components must be deterministic where possible, and properly seeded when involving LLM sampling.
- **Scientific Rigor:** Any new baseline or configuration must be subject to multi-seed statistical evaluation.
- **Separation of Concerns:** Keep researcher, supervisor, and evaluator roles strictly defined.

## Getting Started

1. Clone the repository and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the tests to ensure your environment is set up correctly:
   ```bash
   pytest tests/
   ```

## Contribution Workflow

1. **Open an Issue:** Before undertaking significant work, please open an issue to discuss your proposed changes. This ensures alignment with the research goals and prevents duplicated effort.
2. **Create a Branch:** `git checkout -b feature/your-feature-name`
3. **Commit Your Changes:** Keep commits focused and provide clear, descriptive commit messages.
4. **Pass Tests:** Ensure all unit tests and linting (`ruff`) pass.
5. **Open a Pull Request:** Describe your changes, the problem they solve, and link the relevant issue.

## Adding New Skills

If you are contributing a new Agent Skill to the `research_group/skills/` directory, ensure it includes:
- A clear `SKILL.md` file detailing the prompt and instructions.
- Relevant `references/*.md` providing ground-truth knowledge for the agent.

## Evaluation Protocol

If your contribution involves architectural changes to the multi-agent graph (e.g., modifying supervisors, changing evaluator logic), you are required to run the benchmark suite and provide a statistical comparison against the V1 and V2-full baselines per the `EVALUATION_PROTOCOL.md`.
