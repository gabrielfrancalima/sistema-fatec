import CrudPage from "@/components/CrudPage";

export default function Cursos() {
  return (
    <CrudPage
      title="Cursos"
      endpoint="cursos"
      testid="curso"
      columns={[
        { key: "nome", label: "Nome do curso" },
        { key: "sigla", label: "Sigla" },
        { key: "turno", label: "Turno" },
        { key: "coordenador_nome", label: "Coordenador" },
      ]}
      fields={[
        { name: "nome", label: "Nome do curso", type: "text", required: true },
        { name: "sigla", label: "Sigla", type: "text", required: true },
        { name: "turno", label: "Turno", type: "select", default: "noturno",
          options: [
            { value: "matutino", label: "Matutino" },
            { value: "vespertino", label: "Vespertino" },
            { value: "noturno", label: "Noturno" },
          ] },
        { name: "coordenador_nome", label: "Coordenador", type: "text" },
      ]}
    />
  );
}
