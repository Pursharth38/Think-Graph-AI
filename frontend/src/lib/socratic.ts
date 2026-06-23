import { NodeType } from '../types/graph';

/**
 * Client-side Socratic prompts derived from a node's logical role.
 *
 * SEAM: when a backend /explain (or /socratic) endpoint exists, replace the
 * body of `socraticFor` with a fetch and keep this as the offline fallback.
 */
export interface SocraticCopy {
  roleTitle: string;
  roleSummary: string;
  questions: string[];
}

const BY_TYPE: Record<NodeType, Omit<SocraticCopy, never>> = {
  premise: {
    roleTitle: 'A premise',
    roleSummary:
      'A stated reason offered in support of the conclusion. The argument treats it as given.',
    questions: [
      'Is this claim actually true, or merely asserted?',
      'Would everyone accept it, or is it contestable?',
      'Does the conclusion really follow if this premise holds?',
    ],
  },
  assumption: {
    roleSummary:
      'An unstated bridging claim the argument needs in order to work. It is never written in the text.',
    roleTitle: 'An implicit assumption',
    questions: [
      'If this assumption were false, would the conclusion collapse?',
      'Why might the author have left it unstated?',
      'What evidence would be needed to defend it?',
    ],
  },
  conclusion: {
    roleTitle: 'The conclusion',
    roleSummary: 'The main claim the whole argument is trying to establish.',
    questions: [
      'Do the premises, taken together, actually establish this?',
      'Is the claim stated more strongly than the evidence allows?',
      'What would a counter-argument look like?',
    ],
  },
  sub_conclusion: {
    roleTitle: 'A sub-conclusion',
    roleSummary:
      'An intermediate claim derived from earlier premises, which then itself supports the main conclusion.',
    questions: [
      'Which premises is this derived from?',
      'Is that derivation valid on its own?',
      'Does it carry enough weight to support the final conclusion?',
    ],
  },
  counter_premise: {
    roleTitle: 'A counter-premise',
    roleSummary:
      'A consideration that pushes against the conclusion, often introduced by “however” or “but”.',
    questions: [
      'How does the argument neutralise this objection?',
      'Is it dismissed too quickly?',
      'Could it actually defeat the conclusion?',
    ],
  },
  fallacy: {
    roleTitle: 'A flawed inference',
    roleSummary: 'This step represents an invalid move in the reasoning.',
    questions: [
      'Exactly where does the logic break?',
      'What would a valid version of this step require?',
    ],
  },
};

export function socraticFor(nodeType: NodeType): SocraticCopy {
  return BY_TYPE[nodeType];
}
