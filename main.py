from hotel import HotelSystem
def main():
    N, V = map(int, input("Enter N V : ").split())
    
    hotel = HotelSystem()
    hotel.init_setting(N, V)


if __name__ == "__main__":
    main()