const EXTENSION_TO_KIND: Record<string, string> = {
  stl: "model_stl",
  obj: "model_obj",
  glb: "model_glb",
  gltf: "model_glb",
  "3mf": "model_3mf",
  step: "model_step",
  stp: "model_step",
  png: "source_image",
  jpg: "source_image",
  jpeg: "source_image",
  webp: "source_image",
};

export function inferFileKind(filename: string): string {
  const extension = filename.split(".").pop()?.toLowerCase() ?? "";
  return EXTENSION_TO_KIND[extension] ?? "document";
}
