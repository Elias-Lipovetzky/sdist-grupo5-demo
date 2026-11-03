import argparse
import sys
from urllib.error import URLError

from workflows import (
    demo_rest, demo_overfetch, demo_graphql, demo_nplus1, demo_error, demo_all,
)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    entries = [
        ("rest", demo_rest, "Varios GET para completar una vista"),
        ("overfetch", demo_overfetch, "Un GET agregado con campos sobrantes"),
        ("graphql", demo_graphql, "Seleccion de campos y carga por lote"),
        ("nplus1", demo_nplus1, "Misma query con resolvers ingenuos"),
        ("error", demo_error, "Validacion de un campo inexistente"),
        ("all", demo_all, "Ensayar todos los escenarios"),
    ]
    for name, workflow, help_text in entries:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--base", default="http://localhost:8000")
        command.add_argument("--full", action="store_true", help="Mostrar textos largos sin abreviar")
        command.set_defaults(handler=workflow)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (URLError, TimeoutError, RuntimeError) as exc:
        print(f"Demo interrumpida: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
