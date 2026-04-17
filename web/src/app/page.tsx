import { ClientApp } from "./client-app";

interface HomeProps {
  searchParams: Promise<{ agent?: string }>;
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const agentRole = params.agent === "rob" ? "rob" : "john";

  return <ClientApp agentRole={agentRole} />;
}
