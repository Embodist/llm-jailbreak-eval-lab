export type ModelRow = {
  id: string;
  name: string;
  family: string;
  size: string;
  A: number;
  B: number;
  C: number;
  blocked: number;
  errors: number;
  n: number;
  rate: number | null;
};

export type TechRow = {
  key: string;
  name: string;
  A: number;
  B: number;
  C: number;
  n: number;
  rate: number | null;
};

export type Heatmap = {
  models: string[];
  techniques: string[];
  techniqueNames: string[];
  values: (number | null)[][];
};

export type GoalRow = { goal: string; A: number; B: number; C: number; n: number; rate: number | null };

export type ScaleRow = { label: string; small: ModelRow; large: ModelRow };

export type MultiRow = {
  model: string;
  scenario: string;
  sequence: string[];
  final: string;
  drift: boolean;
};

export type TaxonomyItem = { key: string; zh: string; risk: string };

export type MasterBlock = {
  manifest: {
    total: number;
    core: number;
    by_master_category: Record<string, number>;
    by_label: Record<string, number>;
    by_risk: Record<string, number>;
    master_taxonomy: TaxonomyItem[];
  };
  core: {
    topics: string[];
    topicNames: string[];
    techniqueRates: TechRow[];
    topicMatrix: {
      topics: string[];
      topicNames: string[];
      techniques: string[];
      techniqueNames: string[];
      values: (number | null)[][];
    };
    harmfulRate: number | null;
    complianceRate: number | null;
    falseRefusalRate: number | null;
    counts: { harmful: number; compliance: number };
  };
};

export type FocusTech = { key: string; name: string; C: number; n: number; rate: number | null };

export type FocusBlock = {
  model: string;
  harmful: { C: number; A: number; B: number; n: number; rate: number | null };
  overRefusal: { refused: number; n: number; rate: number | null; byTopic: Record<string, number> };
  main: { C: number; n: number; rate: number | null };
  techniques: FocusTech[];
  family: { id: string; C: number; n: number; rate: number | null }[];
  multi: { scenario: string; sequence: string[]; final: string }[];
  findings: string[];
  caveats: string[];
};

export type DatasetBlock = {
  total: number;
  by_source: Record<string, number>;
  by_master_category: Record<string, number>;
  by_label: Record<string, number>;
  by_risk: Record<string, number>;
  taxonomy: TaxonomyItem[];
  validation: {
    status?: string;
    errors?: string[];
    warnings?: string[];
    core?: { uncovered_cells?: string[] };
  };
  coverage: { gaps?: string[]; dimensions?: Record<string, unknown> };
  generated: { single: number; multi: number };
};

export type CaseItem = {
  id: string;
  kind: "single" | "multi";
  origin: string;
  technique: string | null;
  topic: string | null;
  goal: string | null;
  risk: string | null;
  source: string | null;
  compliance: boolean | null;
  hooks: string;
  prompts: { system: string | null; prompt: string | null; prefill: string | null };
  turns: string[] | null;
  messages: { role: string; content: string }[];
  curl: string;
};

export type CasesResponse = {
  generatedAt: string;
  count: number;
  techniques: string[];
  topics: string[];
  cases: CaseItem[];
};

export type Results = {
  generatedAt: string;
  meta: {
    single: string | null;
    multi: string | null;
    attackProbes: number;
    controlProbes: number;
    models: number;
    multiScenarios: number;
    driftScenarios: number;
    judged: number;
  };
  models: ModelRow[];
  techniques: TechRow[];
  heatmap: Heatmap;
  goals: GoalRow[];
  scale: ScaleRow[];
  multi: MultiRow[];
  blocked: { model: string; probe: string }[];
  master?: MasterBlock;
  focus?: FocusBlock;
  dataset?: DatasetBlock;
};
