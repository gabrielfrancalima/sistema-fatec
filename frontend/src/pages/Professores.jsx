import CrudPage from "@/components/CrudPage";

export default function Professores() {
  return (
    <CrudPage
      title="Professores"
      endpoint="professores"
      testid="professor"
      columns={[
        { key: "nome", label: "Nome" },
        { key: "titulacao", label: "Titulação" },
        { key: "email", label: "E-mail" },
        { key: "cpf", label: "CPF" },
        { key: "registro", label: "Registro" },
      ]}
      fields={[
        { name: "nome", label: "Nome completo", type: "text", required: true },
        { name: "titulacao", label: "Titulação", type: "select", default: "Especialista",
          options: [
            { value: "Graduado", label: "Graduado" },
            { value: "Especialista", label: "Especialista" },
            { value: "Mestre", label: "Mestre" },
            { value: "Doutor", label: "Doutor" },
          ] },
        { name: "email", label: "E-mail", type: "text" },
        { name: "cpf", label: "CPF", type: "text" },
        { name: "registro", label: "Registro funcional", type: "text" },
      ]}
    />
  );
}
