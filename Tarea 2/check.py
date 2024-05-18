#This code check if the both files are the same or not

with open('HP3.txt', "br") as file1:
    with open('HP3.txt', "br") as file2:
        while True:
            line1 = file1.read(1024)
            line2 = file2.read(1024)
            if line1 != line2:
                print("The files are not the same")
                break
            if not line1:
                print("The files are the same")
                break
