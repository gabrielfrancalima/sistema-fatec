import CrudPage from "@/components/CrudPage";

export default function AulasRemotas() {
  return (
    <CrudPage
      title="Aulas Remotas"
      endpoint="aulas-remotas"
      testid="aula-remota"
      columns={[
        { key: "data", label: "Data", type: "date" },
        { key: "curso_id", label: "Curso", type: "ref", refEndpoint: "cursos", refLabel: "nome" },
        { key: "disciplina_id", label: "Disciplina", type: "ref", refEndpoint: "disciplinas", refLabel: "nome" },
        { key: "professor_id", label: "Professor", type: "ref", refEndpoint: "professores", refLabel: "nome" },
        { key: "descricao", label: "Observação" },
      ]}
      fields={[
        { name: "data", label: "Data", type: "date", required: true },
        { name: "curso_id", label: "Curso", type: "ref", refEndpoint: "cursos", refLabel: "nome" },
        { name: "disciplina_id", label: "Disciplina", type: "ref", refEndpoint: "disciplinas", refLabel: "nome" },
        { name: "professor_id", label: "Professor", type: "ref", refEndpoint: "professores", refLabel: "nome" },
        { name: "descricao", label: "Observação", type: "text" },
      ]}
    />
  );
}
