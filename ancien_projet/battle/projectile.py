class Projectile:
    def __init__(self):
        self.shooter= None
        self.position = None
        self.direction = None
        self.speed = None
        self.range= None

        self.travel_dist=0

    def arrow(self, shooter, destination, distance):
        """Crossbow Man Projectile"""

        dx =(destination[0]-shooter.position[0])/distance
        dy= (destination[1] - shooter.position[1])/distance

        self.direction = (dx , dy)
        self.speed = 10
        self.shooter= shooter
        self.position=shooter.position
        self.range=min((distance + 0.5) , (shooter.range + 1.25 )) # Y a besoin d'un peu de marge

        return self
    
    def lance(self, shooter, destination, distance):
        """Elite Skirmisher Projectile"""

        dx =(destination[0]-shooter.position[0])/distance
        dy= (destination[1] - shooter.position[1])/distance

        self.direction = (dx , dy)
        self.speed = 7
        self.shooter= shooter
        self.position=shooter.position
        self.range= min((distance + 0.5) , (shooter.range + 1.25 ))

        return self

    
    