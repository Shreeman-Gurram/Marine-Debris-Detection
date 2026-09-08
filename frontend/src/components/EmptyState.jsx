import { FileSearch } from "lucide-react";

export default function EmptyState({ title, text }) {
  return (
    <div className="empty-state">
      <FileSearch size={38} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
