import { useId } from "react";
import { useDemoUser } from "../auth/DemoUserContext";
import { BUSINESS_LINE_LABELS, DEMO_USERS } from "../auth/demoUsers";

export function AppHeader() {
  const { user, selectUser } = useDemoUser();
  const selectId = useId();
  const linesId = useId();

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <h1 className="app-header__title">Brisamar · Asistente de procedimientos</h1>
        <div className="app-header__user">
          <label htmlFor={selectId} className="field-label">
            Usuario demo
          </label>
          <select
            id={selectId}
            value={user.token}
            onChange={(event) => selectUser(event.target.value)}
            aria-describedby={linesId}
          >
            {DEMO_USERS.map((demoUser) => (
              <option key={demoUser.token} value={demoUser.token}>
                {demoUser.name} ({demoUser.token})
              </option>
            ))}
          </select>
          <p id={linesId} className="app-header__lines">
            Líneas visibles:{" "}
            {user.lines.map((line) => (
              <span key={line} className="tag">
                {BUSINESS_LINE_LABELS[line]}
              </span>
            ))}
          </p>
        </div>
      </div>
    </header>
  );
}
