import snowflake from "snowflake-sdk";

// Read-only: only queries the ANALYTICS schema

let cachedConnection: snowflake.Connection | null = null;

function getConnection(): Promise<snowflake.Connection> {
  if (cachedConnection) {
    return Promise.resolve(cachedConnection);
  }

  const connection = snowflake.createConnection({
    account: process.env.SNOWFLAKE_ACCOUNT!,
    username: process.env.SNOWFLAKE_USER!,
    password: process.env.SNOWFLAKE_PASSWORD!,
    role: process.env.SNOWFLAKE_ROLE || "ACCOUNTADMIN",
    warehouse: process.env.SNOWFLAKE_WAREHOUSE || "CYBERSIGNAL_WH",
    database: process.env.SNOWFLAKE_DATABASE || "CYBERSIGNAL",
    schema: process.env.SNOWFLAKE_SCHEMA || "ANALYTICS",
  });

  return new Promise((resolve, reject) => {
    connection.connect((err, conn) => {
      if (err) {
        reject(err);
        return;
      }
      cachedConnection = conn;
      resolve(conn);
    });
  });
}

export async function query<T = Record<string, unknown>>(
  sqlText: string,
  binds: (string | number)[] = []
): Promise<T[]> {
  const connection = await getConnection();
  return new Promise((resolve, reject) => {
    connection.execute({
      sqlText,
      binds,
      complete: (err, _stmt, rows) => {
        if (err) {
          reject(err);
          return;
        }
        resolve((rows as T[]) || []);
      },
    });
  });
}
