import CrudPage from "@/components/CrudPage";

export default function Feriados() {
  return (
    <CrudPage
      title="Feriados"
      endpoint="feriados"
      testid="feriado"
      columns={[
        { key: "data", label: "Data", type: "date" },
        { key: "descricao", label: "Descrição" },
        { key: "tipo", label: "Tipo" },
      ]}
      fields={[
        { name: "data", label: "Data", type: "date", required: true },
        { name: "descricao", label: "Descrição", type: "text", required: true },
        { name: "tipo", label: "Tipo", type: "select", default: "Nacional",
          options: [
            { value: "Nacional", label: "Nacional" },
            { value: "Estadual", label: "Estadual" },
            { value: "Municipal", label: "Municipal" },
            { value: "Institucional", label: "Institucional" },
          ] },
      ]}
    />
  );
}
