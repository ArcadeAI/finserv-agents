import { ClientApp } from "./client-app";

interface HomeProps {
  searchParams: Promise<{ agent?: string }>;
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const isLive = Boolean(
    process.env.ARCADE_GATEWAY_URL &&
    process.env.ARCADE_API_KEY &&
    process.env.ANTHROPIC_API_KEY
  );

  const agentRole = params.agent === "rob" ? "rob" : "john";

  return <ClientApp isLive={isLive} agentRole={agentRole} />;
}
