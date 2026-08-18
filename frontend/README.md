# SupplierCart - Frontend Code

This directory contains the frontend code for the SupplierCart plugin.

## Architecture

The frontend code is designed to integrate natively with the InvenTree user interface.

### Frameworks

We use Mantine, running on React, to match the InvenTree stack.

- [React](https://react.dev/)
- [Mantine](https://mantine.dev/)

## Project Setup

This project uses [Vite](https://vitejs.dev/) as the build tool. We followed [this guide](https://vitejs.dev/guide/#scaffolding-your-first-vite-project) to scaffold the project.

_Note: The following instructions assume you are already in the `frontend` directory._

### Install Frontend Libraries

Install the required frontend libraries:

```bash
npm install
```

### Translate

If you have translation support enabled, run:

```bash
npm run translate
```

### Building

To compile the frontend code, run:

```bash
npm run build
```

This will compile the frontend into the `../my_plugin/static` directory (ready for distribution).

Note: The target directory is intentionally outside of the frontend directory, so that the compiled files are correctly bundled into the python package install.

### Testing

To run the frontend code in a test environment, run:

```bash
npm run dev
```

This will start a development server (usually on `localhost:5174`) which will automatically reload when changes are made to the source code.

Note: You will also need the InvenTree frontend dev server to be running on `localhost:5173` (using `invoke dev.frontend-server` in the InvenTree project).

### Linting / Formatting

The frontend code is linted and formatted using [biomejs](https://biomejs.dev/).

To _check_ the code for linting errors, run:

```bash
npm run lint
```

To _fix_ any linting errors, run:

```bash
npm run lint:fix
```

Any formatting errors will be automatically fixed when you run the `lint:fix` command.
