export type ControllerNode = {
  body_id: string;
  region: string;
  super_segment?: string;
  hemisphere?: string;
  type?: string;
  transmitter?: string;
};
export type ControllerEdge = { source: number; target: number; weight: number };
export type ConnectomeMap = {
  dataset: string;
  source_kind: string;
  notice?: string;
  neurons: ControllerNode[];
  edges: ControllerEdge[];
};
