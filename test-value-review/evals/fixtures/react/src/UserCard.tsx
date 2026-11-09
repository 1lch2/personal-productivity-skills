import React from "react";

export type User = { name: string; role: string };

export function UserCard({
  user,
  onSelect,
}: {
  user: User;
  onSelect?: () => void;
}) {
  return (
    <article>
      <h2>{user.name}</h2>
      <p>{user.role}</p>
      {onSelect ? <button onClick={onSelect}>Select</button> : null}
    </article>
  );
}
