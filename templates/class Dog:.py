class Dog:
    def __init__(self, name, breed, age):
        self.name = name
        self.breed = breed
        self.age = age
    
    def bark(self):
        print(f"{self.name} barks: Woof!")
    
    def grow_older(self):
        self.age += 1
        print(f"{self.name} is now {self.age} years old.")

# Create a dog object
my_dog = Dog("Buddy", "Golden Retriever", 2)

# Output the dog's information
print(f"Dog Name: {my_dog.name}")
print(f"Breed: {my_dog.breed}")
print(f"Age: {my_dog.age}")

# Make the dog bark
my_dog.bark()

# Make the dog grow older
my_dog.grow_older()
my_dog.grow_older()
my_dog.grow_older()