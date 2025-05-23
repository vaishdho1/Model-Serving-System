
import argparse

'''
The class starts a http server and a grpc server on different ports.
This is run by the ProxyManager class.
'''
class HttpProxy:
   pass





def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--http_port", type=int, default=8000)
    #Start a http server and also a grpc server on different ports
    args = parser.parse_args()

    HttpProxy(args.port)


if __name__ == "__main__":
    main()