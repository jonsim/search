__version__ = '1.0'

def search(regex, paths, command_args, ignore_case=False, verbose=False):
    print 'grep search_result'

def get_subparser(subparsers):
    parser = subparsers.add_parser('files', help='files mode', add_help=False)
    #parser.add_argument('-r', action='store_const',
    #                    const=True, default=False,
    #                    help='Use ripgrep instead of grep')
    return parser
