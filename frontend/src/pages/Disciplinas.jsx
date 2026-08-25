import CrudPage from "@/components/CrudPage";

export default function Disciplinas() {
  return (
    <CrudPage
      title="Disciplinas"
      endpoint="disciplinas"
      testid="disciplina"
      columns={[
        { key: "nome", label: "Disciplina" },
        { key: "codigo", label: "Código" },
        { key: "curso_id", label: "Curso", type: "ref", refEndpoint: "cursos", refLabel: "nome" },
        { key: "professor_id", label: "Professor", type: "ref", refEndpoint: "professores", refLabel: "nome" },
        { key: "aulas_por_semana", label: "Aulas/sem." },
        { key: "carga_horaria", label: "CH" },
      ]}
      fields={[
        { name: "nome", label: "Nome da disciplina", type: "text", required: true },
        { name: "codigo", label: "Código", type: "text", required: true },
        { name: "curso_id", label: "Curso", type: "ref", refEndpoint: "cursos", refLabel: "nome", required: true },
        { name: "professor_id", label: "Professor responsável", type: "ref", refEndpoint: "professores", refLabel: "nome" },
        { name: "aulas_por_semana", label: "Aulas por semana", type: "number", default: 2, required: true },
        { name: "carga_horaria", label: "Carga horária (h)", type: "number", default: 40 },
      ]}
    />
  );
}
