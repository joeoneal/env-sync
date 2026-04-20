import click


class HelpCommand(click.Command):
    def get_help_option(self, ctx):
        return None

    def parse_args(self, ctx, args):
        if args == ["help"]:
            click.echo(self.get_help(ctx))
            ctx.exit()
        return super().parse_args(ctx, args)

    def format_options(self, ctx, formatter):
        records = []
        for param in self.get_params(ctx):
            record = param.get_help_record(ctx)
            if record:
                records.append(record)
        records.append(("help", "Show this message and exit."))

        if records:
            with formatter.section("Options"):
                formatter.write_dl(records)
